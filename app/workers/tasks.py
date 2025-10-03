import logging

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO, CurrentMessage
from periodiq import PeriodiqMiddleware, cron
from safe_eth.eth.utils import fast_to_checksum_address
from safe_eth.util.util import to_0x_hex_str

from app.config import settings
from app.datasources.cache.redis import del_contract_cache
from app.datasources.db.database import db_session_context
from app.datasources.db.models import Contract
from app.loggers.safe_logger import get_task_info, logging_task_context
from app.services.contract_metadata_service import get_contract_metadata_service
from app.services.safe_contracts_service import update_safe_contracts_info


def log_record_factory_for_task(*args, **kwargs):
    """
    Injects to log record the task information.

    :param args:
    :param kwargs:
    :return:
    """
    record = logging.LogRecord(*args, **kwargs)
    try:
        record.task_detail = get_task_info()
    except LookupError:
        pass
    return record


logging.setLogRecordFactory(log_record_factory_for_task)


logger = logging.getLogger(__name__)
redis_broker = RedisBroker(url=settings.REDIS_URL)
redis_broker.add_middleware(PeriodiqMiddleware(skip_delay=60))
redis_broker.add_middleware(AsyncIO())
redis_broker.add_middleware(CurrentMessage())
dramatiq.set_broker(redis_broker)


@dramatiq.actor
def task_to_test(message: str) -> None:
    """
    Examples of use:

        from periodiq import cron
        @dramatiq.actor(periodic=cron("*/2 * * * *"))

        async def task_to_test(message: str) -> None:
    """
    logger.info(f"Message processed! -> {message}")
    return


@dramatiq.actor
@db_session_context
async def get_contract_metadata_task(
    address: str, chain_id: int, skip_attemp_download: bool = False
):
    with logging_task_context(CurrentMessage.get_current_message()):
        contract_metadata_service = get_contract_metadata_service()
        # Just try the first time, following retries should be scheduled
        if (
            skip_attemp_download
            or await contract_metadata_service.should_attempt_download(
                address, chain_id, 0
            )
        ):
            logger.info("Downloading contract metadata")
            contract_metadata = await contract_metadata_service.get_contract_metadata(
                fast_to_checksum_address(address), chain_id
            )
            result = await contract_metadata_service.process_contract_metadata(
                contract_metadata
            )
            if result:
                logger.info("Success download contract metadata")
                # Force invalidate contract cache view
                del_contract_cache(address)
            else:
                logger.info("Failed to download contract metadata")

            if (
                proxy_implementation_address
                := contract_metadata_service.get_proxy_implementation_address(
                    contract_metadata
                )
            ):
                logger.info(
                    "Adding task to download proxy implementation metadata with address %s",
                    proxy_implementation_address,
                )
                get_contract_metadata_task.send(
                    address=proxy_implementation_address, chain_id=chain_id
                )
        else:
            logger.debug("Skipping contract")


@dramatiq.actor(periodic=cron("0 0 * * *"))  # Every midnight
@db_session_context
async def get_missing_contract_metadata_task():
    with logging_task_context(CurrentMessage.get_current_message()):
        async for contract in Contract.get_contracts_without_abi(
            settings.CONTRACT_MAX_DOWNLOAD_RETRIES
        ):
            get_contract_metadata_task.send(
                address=to_0x_hex_str(contract.address),
                chain_id=contract.chain_id,
                skip_attemp_download=True,
            )


@dramatiq.actor(periodic=cron("0 5 * * *"))  # Every day at 5 am
@db_session_context
async def update_proxies_task():
    with logging_task_context(CurrentMessage.get_current_message()):
        async for proxy_contract in Contract.get_proxy_contracts():
            get_contract_metadata_task.send(
                address=to_0x_hex_str(proxy_contract.address),
                chain_id=proxy_contract.chain_id,
                skip_attemp_download=True,
            )


@dramatiq.actor(periodic=cron("0 * * * *"))  # Every hour
@db_session_context
async def update_safe_contracts_info_task():
    with logging_task_context(CurrentMessage.get_current_message()):
        await update_safe_contracts_info()
