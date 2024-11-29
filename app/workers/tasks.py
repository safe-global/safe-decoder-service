import logging
import time
from datetime import datetime

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from periodiq import PeriodiqMiddleware, cron

from app.config import settings

redis_broker = RedisBroker(url=settings.REDIS_URL)
redis_broker.add_middleware(PeriodiqMiddleware(skip_delay=60))

dramatiq.set_broker(redis_broker)


@dramatiq.actor
def example_task(message: str) -> None:
    time.sleep(10)  # Network delay simulation
    logging.info(f"processed! -> {message}")
    return


@dramatiq.actor(periodic=cron("*/2 * * * *"))
def scheduled_example_task() -> None:
    time.sleep(10)  # Network delay simulation
    logging.info(f"processed with crontab! at {datetime.now()}")
    return
