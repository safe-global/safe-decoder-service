# SPDX-License-Identifier: FSL-1.1-MIT
import asyncio
from unittest import mock
from unittest.mock import MagicMock

from eth_account import Account
from hexbytes import HexBytes
from safe_eth.eth import EthereumNetwork
from safe_eth.eth.clients import AsyncEtherscanClientV2
from safe_eth.eth.utils import fast_to_checksum_address
from taskiq.receiver import Receiver

from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import AbiSource, Contract
from app.services.safe_contracts_service import SafeContractsService
from app.workers.tasks import (
    broker,
    build_broker,
    create_safe_contracts_task_for_new_chains,
    get_contract_metadata_task,
    task_to_test,
)

from ...datasources.cache.redis import get_redis
from ...services.contract_metadata_service import ContractMetadataService
from ..datasources.db.async_db_test_case import AsyncDbTestCase
from ..mocks.contract_metadata_mocks import (
    etherscan_metadata_mock,
    etherscan_proxy_metadata_mock,
)


async def wait_tasks_execution(timeout: float = 10.0) -> None:
    redis = get_redis()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        groups = await redis.xinfo_groups("taskiq")
        if not groups or (groups[0]["lag"] == 0 and groups[0]["pending"] == 0):
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Tasks did not drain within the timeout")


class TestTasks(AsyncDbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Flush Redis before startup so the consumer group it declares is not wiped
        await get_redis().flushall()
        # Rebind the broker connection pool to this test's event loop
        broker.connection_pool = build_broker().connection_pool
        await broker.startup()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        await broker.shutdown()
        await get_redis().flushall()

    async def test_task_in_redis_queue(self):
        redis = get_redis()
        self.assertEqual(await redis.xlen("taskiq"), 0)

        await task_to_test.kiq("Task in Redis Queue")

        self.assertEqual(await redis.xlen("taskiq"), 1)
        groups = await redis.xinfo_groups("taskiq")
        self.assertEqual(groups[0]["lag"], 1)

        finish_event = asyncio.Event()
        worker = asyncio.create_task(
            Receiver(broker, run_startup=False, max_async_tasks=10).listen(finish_event)
        )
        await wait_tasks_execution()
        finish_event.set()
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

        groups = await redis.xinfo_groups("taskiq")
        self.assertEqual(groups[0]["lag"], 0)
        self.assertEqual(groups[0]["pending"], 0)


class TestAsyncTasks(AsyncDbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await get_redis().flushall()
        # Rebind the broker connection pool to this test's event loop
        broker.connection_pool = build_broker().connection_pool
        await broker.startup()
        # Consume and run tasks in-process so the patched mocks apply while they execute
        self._finish_event = asyncio.Event()
        self._worker = asyncio.create_task(
            Receiver(broker, run_startup=False, max_async_tasks=10).listen(
                self._finish_event
            )
        )

    async def asyncTearDown(self):
        await super().asyncTearDown()
        # Stop the in-process task consumer
        self._finish_event.set()
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass
        await broker.shutdown()
        await get_redis().flushall()

    @mock.patch.object(ContractMetadataService, "enabled_clients")
    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @db_session_context
    async def test_get_contract_metadata_task(
        self,
        etherscan_get_contract_metadata_mock: MagicMock,
        mock_enabled_clients: MagicMock,
    ):
        contract_address = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
        chain_id = 100
        cache_key = f"should_attempt_download:{contract_address}:{chain_id}:0"
        redis = get_redis()
        await redis.delete(cache_key)
        await AbiSource(name="Etherscan", url="").create()
        await db_session.commit()
        etherscan_get_contract_metadata_mock.return_value = None
        mock_enabled_clients.return_value = [
            AsyncEtherscanClientV2(EthereumNetwork(chain_id))
        ]
        # Should try one time
        await get_contract_metadata_task.kiq(
            address=contract_address, chain_id=chain_id
        )
        await wait_tasks_execution()
        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # Shouldn't try second time
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        chain_id = 100
        await get_contract_metadata_task.kiq(
            address=contract_address, chain_id=chain_id
        )
        await wait_tasks_execution()
        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # After reset cache and database retries should download the contract
        contract.fetch_retries = 0
        await redis.delete(cache_key)
        await contract.update()
        await db_session.commit()
        await get_contract_metadata_task.kiq(
            address=contract_address, chain_id=chain_id
        )
        await wait_tasks_execution()
        await db_session.refresh(contract)
        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertIsNotNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 2)

    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @db_session_context
    async def test_get_contract_metadata_task_with_proxy(
        self, etherscan_get_contract_metadata_mock: MagicMock
    ):
        await AbiSource(name="Etherscan", url="").create()
        await db_session.commit()
        etherscan_get_contract_metadata_mock.side_effect = [
            etherscan_proxy_metadata_mock,
            etherscan_metadata_mock,
        ]
        contract_address = Account.create().address
        proxy_implementation_address = "0x43506849D7C04F9138D1A2050bbF3A0c054402dd"
        chain_id = 1

        await get_contract_metadata_task.kiq(
            address=contract_address, chain_id=chain_id
        )

        await wait_tasks_execution()

        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertEqual(
            fast_to_checksum_address(contract.implementation),
            proxy_implementation_address,
        )
        proxy_implementation = await Contract.get_contract(
            HexBytes(proxy_implementation_address), chain_id
        )
        self.assertIsNotNone(proxy_implementation)
        self.assertEqual(contract.implementation, proxy_implementation.address)

        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 2)

    @db_session_context
    async def test_create_safe_contracts_task_for_new_chains(self):
        from app.config import settings

        new_chain_id = 999

        deployments = SafeContractsService._get_default_deployments_by_version()
        expected_count = len(deployments)
        safe_addresses: set[bytes] = {
            HexBytes(address) for _, _, address in deployments
        }

        exists_before = await Contract.exists_safe_contracts(
            new_chain_id, safe_addresses
        )
        self.assertFalse(exists_before)

        lock_key = f"lock:create_safe_contracts:{new_chain_id}"
        redis = get_redis()
        await redis.delete(lock_key)

        await create_safe_contracts_task_for_new_chains.kiq(chain_id=new_chain_id)
        await wait_tasks_execution()

        contracts = await Contract.get_all()
        chain_contracts = [c for c in contracts if c.chain_id == new_chain_id]
        self.assertEqual(len(chain_contracts), expected_count)

        for _, contract_name, contract_address in deployments:
            contract = await Contract.get_contract(
                address=HexBytes(contract_address), chain_id=new_chain_id
            )
            self.assertIsNotNone(contract, f"Contract {contract_name} not found")
            self.assertEqual(contract.name, contract_name)
            self.assertIsNotNone(contract.display_name)
            expected_trusted = (
                contract_name in settings.CONTRACTS_TRUSTED_FOR_DELEGATE_CALL
            )
            self.assertEqual(contract.trusted_for_delegate_call, expected_trusted)

        exists_after = await Contract.exists_safe_contracts(
            new_chain_id, safe_addresses
        )
        self.assertTrue(exists_after)

        self.assertFalse(await redis.exists(lock_key))

    @db_session_context
    async def test_create_safe_contracts_task_with_lock_held(self):
        new_chain_id = 888
        lock_key = f"lock:create_safe_contracts:{new_chain_id}"
        redis = get_redis()

        await redis.set(lock_key, "1", ex=300)

        await create_safe_contracts_task_for_new_chains.kiq(chain_id=new_chain_id)
        await wait_tasks_execution()

        contracts = await Contract.get_all()
        chain_contracts = [c for c in contracts if c.chain_id == new_chain_id]
        self.assertEqual(len(chain_contracts), 0)

        await redis.delete(lock_key)
