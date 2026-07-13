# SPDX-License-Identifier: FSL-1.1-MIT
import unittest
from collections.abc import Awaitable
from typing import cast

from eth_account import Account

from app.datasources.cache.redis import (
    del_contract_cache,
    get_field_key_for_implementation,
    get_field_key_for_selectors,
    get_key_for_contract_selectors,
    get_redis,
)


class TestRedisSelectorsCache(unittest.IsolatedAsyncioTestCase):
    async def test_del_contract_cache_clears_selectors_and_implementation(self):
        """
        `del_contract_cache` must drop the whole per-contract decoding hash: both the
        selectors and the implementation fields, across all chains.
        """
        redis = get_redis()
        address = Account.create().address
        redis_key = get_key_for_contract_selectors(address)

        await cast(
            Awaitable[int],
            redis.hset(
                redis_key,
                mapping={
                    get_field_key_for_selectors(1): "{}",
                    get_field_key_for_selectors(None): "{}",
                    get_field_key_for_implementation(1): '"0x"',
                },
            ),
        )

        await del_contract_cache(address)

        self.assertFalse(await redis.exists(redis_key))
