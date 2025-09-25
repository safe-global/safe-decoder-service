import hashlib
import json
from functools import cache, wraps
from typing import Callable, cast

from pydantic import BaseModel

from redis import Redis

from ...config import settings


@cache
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def cache_contract_key_builder(address: str, **kwargs) -> str:
    return f"contract:{address.lower()}"


def del_contract_key(address: str):
    get_redis().unlink(cache_contract_key_builder(address))


def get_field_key(kwargs: dict) -> str:

    # Ignore request if is part of the parameters
    cacheable_kwargs = {
        k: v for k, v in kwargs.items() if k != "request" and "request" not in k.lower()
    }
    raw_key = json.dumps(cacheable_kwargs, sort_keys=True, default=str)
    return hashlib.md5(raw_key.encode()).hexdigest()


def cache_response(
    key_builder: Callable[..., str], model: type[BaseModel], expire: int = 60
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Serialize arguments to create a cache key
            hash_key = key_builder(**kwargs)
            field_key = get_field_key(kwargs)

            # Try to fetch from Redis cache
            redis = get_redis()
            cached_response = redis.hget(hash_key, field_key)
            if cached_response:
                # Return cached response if it exists
                return json.loads(cast(str, cached_response))

            # Call the original endpoint if no cache
            response = await func(*args, **kwargs)

            # Store the response in cache for later
            # Force validation to trigger field validators that convert bytes
            validated_response = model.model_validate(response)
            redis.hset(
                hash_key, field_key, validated_response.model_dump_json(by_alias=True)
            )
            # Set expiration just if is not configured
            if redis.ttl(hash_key) == -1:
                redis.expire(hash_key, expire)

            return response

        return wrapper

    return decorator
