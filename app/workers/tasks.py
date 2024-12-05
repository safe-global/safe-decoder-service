import logging
import random
import time
from datetime import datetime

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from periodiq import PeriodiqMiddleware, cron

from app.config import settings
from app.services.contract import ContractService

redis_broker = RedisBroker(url=settings.REDIS_URL)
redis_broker.add_middleware(PeriodiqMiddleware(skip_delay=60))
redis_broker.add_middleware(AsyncIO())

dramatiq.set_broker(redis_broker)


@dramatiq.actor
def example_task(message: str) -> None:
    logging.info(f"Example processed! -> {message}")
    return


@dramatiq.actor(periodic=cron("*/2 * * * *"))
def scheduled_example_task() -> None:
    time.sleep(10)  # Network delay simulation
    logging.info(f"processed with crontab! at {datetime.now()}")
    return


@dramatiq.actor
async def create_random_contract():
    logging.info("INIT! -> create_random_contract")
    contract_service = ContractService()
    address = bytes({random.randint(1, 100)})
    contract = await contract_service.create(address=address, name="Example Contract")
    logging.info(f"Contract processed! -> {contract}")
