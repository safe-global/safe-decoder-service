import logging

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from periodiq import PeriodiqMiddleware
from safe_eth.eth.utils import fast_to_checksum_address
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings
from ..datasources.db.database import database_session
from ..services.contract_metadata_service import get_contract_metadata_service

logger = logging.getLogger(__name__)

redis_broker = RedisBroker(url=settings.REDIS_URL)
redis_broker.add_middleware(PeriodiqMiddleware(skip_delay=60))
redis_broker.add_middleware(AsyncIO())

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
@database_session
async def get_contract_metadata_task(
    address: str, chain_id: int, session: AsyncSession
) -> None:
    contract_metadata_service = get_contract_metadata_service()
    # Just try the first time, following retries should be scheduled
    if await contract_metadata_service.should_attempt_download(
        session, address, chain_id, 0
    ):
        logger.info(
            "Downloading contract metadata for contract=%s and chain=%s",
            address,
            chain_id,
        )
        contract_metadata = await contract_metadata_service.get_contract_metadata(
            fast_to_checksum_address(address), chain_id
        )
        result = await contract_metadata_service.process_contract_metadata(
            session, contract_metadata
        )
        if result:
            logger.info(
                "Success download contract metadata for contract=%s and chain=%s",
                address,
                chain_id,
            )
        else:
            logger.info(
                "Failed to download contract metadata for contract=%s and chain=%s",
                address,
                chain_id,
            )

        if proxy_implementation_address := contract_metadata_service.get_proxy_implementation_address(
            contract_metadata
        ):
            logger.info(
                "Adding task to download proxy implementation metadata from address=%s for contract=%s and chain=%s",
                proxy_implementation_address,
                address,
                chain_id,
            )
            get_contract_metadata_task.send(proxy_implementation_address, chain_id)
    else:
        logger.debug("Skipping contract=%s and chain=%s", address, chain_id)
