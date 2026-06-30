# SPDX-License-Identifier: FSL-1.1-MIT
import unittest
from collections.abc import Awaitable
from typing import cast

from eth_account import Account

from app.datasources.cache.redis import (
    del_contract_selectors_cache,
    get_field_key_for_selectors,
    get_key_for_contract_selectors,
    get_redis,
)


class TestRedisSelectorsCache(unittest.IsolatedAsyncioTestCase):
    async def test_del_contract_selectors_cache_also_clears_chainless_field(self):
        """
        Deleting the selectors cache for a specific chain must also drop the
        chain-agnostic (`None`) field, while leaving other chains untouched.
        """
        redis = get_redis()
        address = Account.create().address
        redis_key = get_key_for_contract_selectors(address)
        chain_field = get_field_key_for_selectors(1)
        chainless_field = get_field_key_for_selectors(None)
        other_chain_field = get_field_key_for_selectors(2)

        await cast(
            Awaitable[int],
            redis.hset(
                redis_key,
                mapping={
                    chain_field: "{}",
                    chainless_field: "{}",
                    other_chain_field: "{}",
                },
            ),
        )

        await del_contract_selectors_cache(address, 1)

        # Target chain and the chainless field are gone...
        self.assertFalse(await redis.hexists(redis_key, chain_field))  # type: ignore[misc]
        self.assertFalse(await redis.hexists(redis_key, chainless_field))  # type: ignore[misc]
        # ...but other chains are untouched
        self.assertTrue(await redis.hexists(redis_key, other_chain_field))  # type: ignore[misc]

        await redis.unlink(redis_key)
