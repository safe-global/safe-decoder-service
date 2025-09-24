import hashlib
import json
from functools import cache, wraps
from typing import Callable

from pydantic import BaseModel

from redis.asyncio import Redis

from ...config import settings


@cache
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def get_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    # Filter out non-cacheable parameters
    cache_kwargs = {
        k: v
        for k, v in kwargs.items()
        if not k.startswith("request") and "request" not in k.lower()
    }
    raw_key = f"{func.__module__}.{func.__name__}:{json.dumps(args, default=str, sort_keys=True)}:{json.dumps(cache_kwargs, default=str, sort_keys=True)}"
    return hashlib.md5(raw_key.encode()).hexdigest()


def cache_response(model: type[BaseModel], expire: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Serialize arguments to create a cache key
            cache_key = get_cache_key(func, args, kwargs)
            # Try to fetch from Redis cache
            redis = get_redis()
            cached_response = await redis.get(cache_key)
            if cached_response:
                # Return cached response if it exists
                return json.loads(cached_response)

            # Call the original endpoint if no cache
            response = await func(*args, **kwargs)

            # Store the response in cache for later
            # Force validation to trigger field validators that convert bytes
            validated_response = model.model_validate(response)
            await redis.setex(
                cache_key, expire, validated_response.model_dump_json(by_alias=True)
            )
            return response

        return wrapper

    return decorator
