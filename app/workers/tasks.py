# SPDX-License-Identifier: FSL-1.1-MIT
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import Token

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from safe_eth.eth.utils import fast_to_checksum_address
from safe_eth.util.util import to_0x_hex_str
from taskiq import (
    AsyncBroker,
    SmartRetryMiddleware,
    TaskiqMessage,
    TaskiqMiddleware,
    TaskiqResult,
    TaskiqScheduler,
)
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from app.config import settings
from app.datasources.cache.redis import del_contract_cache, get_redis
from app.datasources.db.database import transactional_session_context
from app.datasources.db.models import Contract
from app.loggers.safe_logger import (
    TaskInfo,
    reset_task_context,
    set_task_context,
)
from app.services.contract_metadata_service import get_contract_metadata_service
from app.services.safe_contracts_service import get_safe_contract_service

logger = logging.getLogger(__name__)


class DeleteOnAckRedisStreamBroker(RedisStreamBroker):
    """
    RedisStreamBroker that removes entries from the stream once acknowledged.

    XACK only clears the pending entries list of the consumer group, the entry
    itself stays in the append only stream forever, so the stream grows with
    every task ever enqueued. Deleting on ack keeps the stream size proportional
    to the messages in flight. Both commands run in a single transaction so an
    acknowledged entry is never left behind.
    """

    def _ack_generator(self, id: str, queue_name: str) -> Callable[[], Awaitable[None]]:
        async def _ack() -> None:
            async with Redis(connection_pool=self.connection_pool) as redis_conn:
                async with redis_conn.pipeline(transaction=True) as pipe:
                    pipe.xack(queue_name, self.consumer_group_name, id)
                    pipe.xdel(queue_name, id)
                    await pipe.execute()

        return _ack


class TaskLoggingMiddleware(TaskiqMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self._tokens: dict[str, Token[TaskInfo]] = {}

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        self._tokens[message.task_id] = set_task_context(message)
        return message

    def _close(self, message: TaskiqMessage) -> None:
        token = self._tokens.pop(message.task_id, None)
        if token is not None:
            reset_task_context(token)

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        self._close(message)

    def on_error(
        self, message: TaskiqMessage, result: TaskiqResult, exception: BaseException
    ) -> None:
        self._close(message)


def build_broker() -> RedisStreamBroker:
    return DeleteOnAckRedisStreamBroker(
        url=settings.REDIS_URL,
        socket_keepalive=True,
        health_check_interval=30,
        retry=Retry(ExponentialBackoff(), retries=5),
        retry_on_error=[RedisConnectionError, RedisTimeoutError],
    ).with_middlewares(
        TaskLoggingMiddleware(),
        SmartRetryMiddleware(
            default_retry_count=5,
            default_retry_label=True,
            default_delay=5,
            use_jitter=True,
            use_delay_exponent=True,
        ),
    )


broker = build_broker()
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])


@asynccontextmanager
async def broker_connection() -> AsyncIterator[AsyncBroker]:
    await broker.startup()
    try:
        yield broker
    finally:
        await broker.shutdown()


@broker.task
async def task_to_test(message: str) -> None:
    logger.info("Message processed! -> %s", message)


@broker.task
async def get_contract_metadata_task(
    address: str, chain_id: int, skip_attempt_download: bool = False
):
    contract_metadata_service = get_contract_metadata_service()
    # Just try the first time, following retries should be scheduled
    should_download = (
        skip_attempt_download
        or await contract_metadata_service.should_attempt_download(address, chain_id, 0)
    )
    if should_download:
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
            await del_contract_cache(address)
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
            await get_contract_metadata_task.kiq(
                address=proxy_implementation_address, chain_id=chain_id
            )
    else:
        logger.debug("Skipping contract")


@broker.task(schedule=[{"cron": "0 0 * * *"}])  # Every midnight
async def get_missing_contract_metadata_task():
    async with transactional_session_context():
        targets = [
            (to_0x_hex_str(contract.address), contract.chain_id)
            async for contract in Contract.get_contracts_without_abi(
                settings.CONTRACT_MAX_DOWNLOAD_RETRIES
            )
        ]
    for address, chain_id in targets:
        await get_contract_metadata_task.kiq(
            address=address,
            chain_id=chain_id,
            skip_attempt_download=True,
        )


@broker.task(schedule=[{"cron": "0 5 * * *"}])  # Every day at 5 am
async def update_proxies_task():
    async with transactional_session_context():
        targets = [
            (to_0x_hex_str(proxy_contract.address), proxy_contract.chain_id)
            async for proxy_contract in Contract.get_proxy_contracts()
        ]
    for address, chain_id in targets:
        await get_contract_metadata_task.kiq(
            address=address,
            chain_id=chain_id,
            skip_attempt_download=True,
        )


@broker.task(schedule=[{"cron": "0 * * * *"}])  # Every hour
async def update_safe_contracts_info_task():
    await get_safe_contract_service().update_safe_contracts_info()


@broker.task
async def create_safe_contracts_task_for_new_chains(chain_id: int):
    lock_key = f"lock:create_safe_contracts:{chain_id}"
    redis = get_redis()
    lock_acquired = await redis.set(lock_key, "1", nx=True, ex=300)

    if not lock_acquired:
        logger.debug(
            "Another task is already creating Safe contracts for chain %d", chain_id
        )
        return

    try:
        safe_contract_service = get_safe_contract_service()
        logger.info("Creating Safe contracts for chain %d", chain_id)
        await safe_contract_service.create_safe_contracts(chain_id=chain_id)
    finally:
        await redis.delete(lock_key)
