"""
Base settings file for FastApi application.
"""

import os
import secrets

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
    RABBITMQ_AMQP_URL: str = "amqp://guest:guest@"
    RABBITMQ_AMQP_EXCHANGE: str = "safe-transaction-service-events"
    RABBITMQ_DECODER_EVENTS_QUEUE_NAME: str = "safe-decoder-service"
    SECRET_KEY: str = secrets.token_urlsafe(
        32
    )  # In production it must be defined so it doesn't change
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_TOKEN_EXPIRATION_SECONDS: int = (
        7 * 24 * 60 * 60
    )  # Admin token expires in 1 week
    ETHERSCAN_API_KEY: str = ""
    ETHERSCAN_MAX_REQUESTS: int = 1000
    BLOCKSCOUT_API_KEY: str = ""
    BLOCKSCOUT_MAX_REQUESTS: int = 1000
    SOURCIFY_API_KEY: str = ""
    SOURCIFY_MAX_REQUESTS: int = 2


settings = Settings()
