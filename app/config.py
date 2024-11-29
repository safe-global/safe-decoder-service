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
    REDIS_URL: str = "redis://"
    DATABASE_URL: str = "psql://postgres:"
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_QUEUE_NAME: str = ""


settings = Settings()
