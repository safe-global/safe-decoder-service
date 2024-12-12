from functools import cache

from redis import Redis

from app.config import settings


@cache
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)
