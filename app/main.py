import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import Response

from app.loggers.safe_logger import HttpRequestLog, HttpResponseLog

from . import VERSION
from .datasources.db.database import (
    _get_database_session_context,
    db_session,
    set_database_session_context,
)
from .datasources.queue.exceptions import QueueProviderUnableToConnectException
from .datasources.queue.queue_provider import QueueProvider
from .routers import about, admin, contracts, data_decoder, default
from .services.abis import AbiService
from .services.data_decoder import get_data_decoder_service
from .services.events import EventsService

logger = logging.getLogger()


def log_record_factory_for_request(*args, **kwargs) -> logging.LogRecord:
    """
    Inject session database identifier in log record.

    :param args:
    :param kwargs:
    :return:
    """
    # Create a log record with additional context
    record = logging.LogRecord(*args, **kwargs)
    try:
        record.db_session = _get_database_session_context()
    except LookupError:
        # This error means that there is not session
        pass

    return record


logging.setLogRecordFactory(log_record_factory_for_request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Define the lifespan of the application:
    - At startup:
         - Connects to the QueueProvider.
         - Load hardcoded ABIs in database
         - Initializes DataDecoderService
    - At shutdown:
        - Disconnects from the QueueProvider.
    """
    queue_provider = QueueProvider()
    consume_task = None
    abi_service = AbiService()
    try:
        loop = asyncio.get_running_loop()
        try:
            logger.debug("Connecting to Queue Provider")
            await queue_provider.connect(loop)
            logger.debug("Connected to Queue Provider")
        except QueueProviderUnableToConnectException as e:
            logger.error("Unable to connect to Queue Provider %s", e)
        if queue_provider.is_connected():
            events_service = EventsService()
            consume_task = asyncio.create_task(
                queue_provider.consume(events_service.process_event)
            )
            logger.debug("Created task to consume elements from Queue Provider")

        with set_database_session_context("InitializeDataDecoderServiceOnStartup"):
            # Load hardcoded ABIs in database
            await abi_service.load_local_abis_in_database()
            # Initializes DataDecoderService
            await get_data_decoder_service()
        yield
    finally:
        if consume_task:
            consume_task.cancel()
        await queue_provider.disconnect()


app = FastAPI(
    title="Safe Decoder Service",
    description="Safe Core{API} decoder service",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
admin.load_admin(app)

# Router configuration
api_v1_router = APIRouter(
    prefix="/api/v1",
)
api_v1_router.include_router(about.router)
api_v1_router.include_router(contracts.router)
api_v1_router.include_router(data_decoder.router)
app.include_router(api_v1_router)
app.include_router(default.router)


@app.middleware("http")
async def http_redirect_middleware(request: Request, call_next):
    """
    Intercepts HTTP response redirects and updates the Location header when behind a proxy.

    This middleware handles cases where the application is deployed behind a reverse proxy
    that forwards requests with custom headers. When a redirect response is generated,
    it ensures the Location header reflects the correct external URL by incorporating
    proxy forwarding headers.

    Args:
        request (Request): The incoming HTTP request object
        call_next: The next middleware/handler in the chain

    Returns:
        Response: The HTTP response, potentially with an updated Location header

    Proxy Headers Used:
        - x-forwarded-prefix: Path prefix to prepend to the redirect location
        - x-forwarded-host: External hostname visible to clients
        - x-forwarded-proto: External protocol (http/https)
        - x-forwarded-port: External port number
    """
    response = await call_next(request)
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    if "location" in response.headers and prefix:
        original_url = URL(response.headers["location"])
        host = request.headers.get("x-forwarded-host")
        protocol = request.headers.get("x-forwarded-proto")
        port = request.headers.get("x-forwarded-port")
        response.headers["location"] = str(
            original_url.replace(
                scheme=protocol,
                hostname=host,
                port=port,
                path=prefix + original_url.path,
            )
        )
    return response


@app.middleware("http")
async def http_request_middleware(request: Request, call_next):
    """
    Intercepts request and do some actions:
     - Set the database session context for the current request, so the same database session is used across the whole request.
     - Log requests calls

    :param request:
    :param call_next:
    :return:
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    with set_database_session_context():
        response: Response | None = None
        try:
            response = await call_next(request)
        except Exception as e:
            raise e
        finally:
            await db_session.remove()
            # Log request
            try:
                end_time = datetime.datetime.now(datetime.timezone.utc)
                total_time = (
                    end_time - start_time
                ).total_seconds() * 1000  # time in ms
                route = request.scope.get("route")
                http_request = HttpRequestLog(
                    url=str(request.url),
                    route=route.path if route else None,
                    method=request.method,
                    startTime=start_time,
                )
                status_code = response.status_code if response else 500
                http_response = HttpResponseLog(
                    status=status_code,
                    endTime=end_time,
                    totalTime=int(total_time),
                )
                logger.info(
                    "Http request",
                    extra={
                        "http_response": http_response.model_dump(),
                        "http_request": http_request.model_dump(),
                    },
                )
            except ValueError as e:
                logger.error(f"Validation log error {e}")

    return response
