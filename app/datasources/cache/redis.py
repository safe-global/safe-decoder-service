import hashlib
import json
from functools import cache, wraps
from typing import Callable, cast

from pydantic import BaseModel

from redis import Redis

from ...config import settings
from ...utils import get_proxy_aware_url


@cache
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def cache_contract_key_builder(address: str, **kwargs) -> str:
    """
    Build the Redis cache key for a contract by its address.

    :param address: The contract address to use as key identifier.
    :param kwargs: Optional additional arguments (ignored).
    :return: A string cache key in the format 'contract:<address>'.
    """
    return f"contract:{address.lower()}"


def del_contract_key(address: str):
    """
    Delete the Redis cache entry for a specific contract by address.

    :param address: The contract address used to build the cache key.
    :return: None
    """
    get_redis().unlink(cache_contract_key_builder(address))


def get_field_key(kwargs: dict) -> str:
    """
    Generate a hashed cache key from the given keyword arguments,
    excluding any request-related data.

    :param kwargs: Dictionary of keyword arguments passed to the endpoint.
    :return: An MD5 hash string representing the filtered and serialized kwargs.
    """
    # Ignore request if it's part of the parameters
    request = kwargs.get("request")
    url_path = ""
    if request:
        url_path = str(get_proxy_aware_url(request))
    cacheable_kwargs = {
        k: v for k, v in kwargs.items() if k != "request" and "request" not in k.lower()
    }
    payload = {"url": url_path, **cacheable_kwargs}
    raw_key = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.md5(raw_key.encode()).hexdigest()


def cache_response(
    key_builder: Callable[..., str], model: type[BaseModel], expire: int = 60
):
    """
    Cache the response of an endpoint in Redis using a hash structure.

    The cache key is composed of a hash key (based on the resource, e.g., contract address)
    and a field key (based on filtered function kwargs). If a cached value exists, it is
    returned directly. Otherwise, the decorated function is called, and its response is
    validated and cached.

    :param key_builder: Function that builds the Redis hash key from kwargs.
    :param model: Pydantic model used to validate and serialize the response.
    :param expire: Expiration time for the Redis key in seconds (default: 60).
    :return: The original or cached response.
    """

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
