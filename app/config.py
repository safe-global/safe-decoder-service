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
    REDIS_URL: str = "redis://"
    DATABASE_URL: str = "psql://postgres:"
    DATABASE_POOL_CLASS: str = "AsyncAdaptedQueuePool"
    DATABASE_POOL_SIZE: int = 10
    TEST: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(
        32
    )  # In production it must be defined so it doesn't change
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"


settings = Settings()
