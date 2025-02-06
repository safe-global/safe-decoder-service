import logging

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO, CurrentMessage
from hexbytes import HexBytes
from periodiq import PeriodiqMiddleware, cron
from safe_eth.eth.utils import fast_to_checksum_address

from app.config import settings
from app.custom_logger import get_task_info, logging_task_context
from app.datasources.db.database import db_session_context
from app.datasources.db.models import Contract
from app.services.contract_metadata_service import get_contract_metadata_service


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
def test_task(message: str) -> None:
    """
    Examples of use:

        from periodiq import cron
        @dramatiq.actor(periodic=cron("*/2 * * * *"))

        async def test_task(message: str) -> None:
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
            # TODO Check if contract is MultiSend. In that case, get the transaction and decode it
            contract_metadata = await contract_metadata_service.get_contract_metadata(
                fast_to_checksum_address(address), chain_id
            )
            result = await contract_metadata_service.process_contract_metadata(
                contract_metadata
            )
            if result:
                logger.info("Success download contract metadata")
            else:
                logger.info("Failed to download contract metadata")

            if proxy_implementation_address := contract_metadata_service.get_proxy_implementation_address(
                contract_metadata
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
                address=HexBytes(contract.address).hex(),
                chain_id=contract.chain_id,
                skip_attemp_download=True,
            )


@dramatiq.actor(periodic=cron("0 5 * * *"))  # Every day at 5 am
@db_session_context
async def update_proxies_task():
    with logging_task_context(CurrentMessage.get_current_message()):
        async for proxy_contract in Contract.get_proxy_contracts():
            get_contract_metadata_task.send(
                address=HexBytes(proxy_contract.address).hex(),
                chain_id=proxy_contract.chain_id,
                skip_attemp_download=True,
            )
