"""
Base settings file for FastApi application.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True,
    )
    TEST: bool = False
    REDIS_URL: str = "redis://"
    DATABASE_URL: str = "psql://postgres:"
    DATABASE_POOL_CLASS: str = "AsyncAdaptedQueuePool"
    DATABASE_POOL_SIZE: int = 10
    RABBITMQ_AMPQ_URL: str = "amqp://guest:guest@"
    RABBITMQ_AMQP_EXCHANGE: str = "safe-transaction-service-events"
    RABBITMQ_DECODER_EVENTS_QUEUE_NAME: str = "safe-decoder-service"


settings = Settings()
