import logging

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from periodiq import PeriodiqMiddleware

from app.config import settings

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
    logging.info(f"Message processed! -> {message}")
    return
