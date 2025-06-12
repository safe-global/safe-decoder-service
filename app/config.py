"""
Base settings file for FastApi application.
"""

import logging.config
import os
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.loggers.safe_logger import SafeJsonFormatter


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True,
    )
    TEST: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_LEVEL_EVENTS_SERVICE: str = "DEBUG"
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
    ETHERSCAN_MAX_REQUESTS: int = 1
    BLOCKSCOUT_MAX_REQUESTS: int = 1
    SOURCIFY_MAX_REQUESTS: int = 100
    CONTRACT_MAX_DOWNLOAD_RETRIES: int = (
        90  # Task running once per day, means 3 months trying.
    )
    CONTRACT_LOGO_BASE_URL: str = (
        "https://safe-transaction-assets.safe.global/contracts/logos"
    )
    CONTRACTS_TRUSTED_FOR_DELEGATE_CALL: list[str] = [
        "MultiSendCallOnly",
        "SignMessageLib",
        "SafeMigration",
    ]


settings = Settings()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": SafeJsonFormatter}},  # Custom formatter class
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "loggers": {
        "": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
            "propagate": False,
        },
        "app.services.events": {
            "level": settings.LOG_LEVEL_EVENTS_SERVICE,
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
