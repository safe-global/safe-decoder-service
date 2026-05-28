# SPDX-License-Identifier: FSL-1.1-MIT
import json
import unittest
from collections.abc import Awaitable
from typing import Any
from unittest import mock
from unittest.mock import MagicMock

from dramatiq.worker import Worker
from eth_account import Account
from eth_typing import Address
from hexbytes import HexBytes
from safe_eth.eth import EthereumNetwork
from safe_eth.eth.clients import AsyncEtherscanClientV2, ContractMetadata
from safe_eth.eth.constants import NULL_ADDRESS
from safe_eth.eth.utils import fast_to_checksum_address, get_empty_tx_params
from web3 import Web3

from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract
from app.services.safe_contracts_service import SafeContractsService
from app.workers.tasks import (
    create_safe_contracts_task_for_new_chains,
    get_contract_metadata_task,
    get_proxy_implementation_metadata_task,
    redis_broker,
    task_to_test,
)

from ...datasources.cache.redis import (
    get_field_key_for_selectors,
    get_key_for_contract_selectors,
    get_redis,
)
from ...services.contract_metadata_service import ContractMetadataService
from ...services.data_decoder import DataDecoderService
from ..datasources.db.async_db_test_case import AsyncDbTestCase
from ..mocks.contract_metadata_mocks import (
    etherscan_metadata_mock,
    etherscan_proxy_metadata_mock,
)
from ..services.mocks_data_decoder import example_abi, example_swapped_abi


class TestTasks(unittest.TestCase):
    worker: Worker

    def setUp(self) -> None:
        redis_broker.client.flushall()
        self.worker = Worker(redis_broker)

    def tearDown(self) -> None:
        redis_broker.client.flushall()
        self.worker.stop()

    def test_task_in_redis_queue(self):
        redis_tasks: Awaitable[list] | list = redis_broker.client.lrange(
            "dramatiq:default", 0, -1
        )
        assert isinstance(redis_tasks, list)
        self.assertEqual(len(redis_tasks), 0)

        test_message = "Task in Redis Queue"
        task_to_test.send(test_message)

        redis_tasks = redis_broker.client.lrange("dramatiq:default", 0, -1)
        assert isinstance(redis_tasks, list)
        self.assertEqual(len(redis_tasks), 1)
        task_id = redis_tasks[0]
        task_info_raw: Any = redis_broker.client.hget("dramatiq:default.msgs", task_id)
        assert isinstance(task_info_raw, bytes)
        task_info = json.loads(task_info_raw)
        self.assertEqual(task_info.get("args"), [test_message])
        self.assertEqual(task_info.get("actor_name"), "task_to_test")

        self.worker.start()

        redis_tasks = redis_broker.client.lrange("dramatiq:default", 0, -1)
        assert isinstance(redis_tasks, list)
        self.assertEqual(len(redis_tasks), 0)


class TestAsyncTasks(AsyncDbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.worker = Worker(redis_broker, worker_threads=1)
        self.worker.start()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.worker.stop()
        redis = get_redis()
        await redis.flushall()

    def _wait_tasks_execution(self):
        # Ensure that all the messages on redis were consumed
        redis_tasks = self.worker.broker.client.lrange("dramatiq:default", 0, -1)
        while len(redis_tasks) > 0:
            redis_tasks = self.worker.broker.client.lrange("dramatiq:default", 0, -1)

        # Wait for all the messages on the given queue to be processed.
        # This method is only meant to be used in tests
        self.worker.broker.join("default")

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
        etherscan_get_contract_metadata_mock.return_value = None
        mock_enabled_clients.return_value = [
            AsyncEtherscanClientV2(EthereumNetwork(chain_id))
        ]
        # Should try one time
        get_contract_metadata_task.send(address=contract_address, chain_id=chain_id)
        self._wait_tasks_execution()
        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # Shouldn't try second time
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        chain_id = 100
        get_contract_metadata_task.send(address=contract_address, chain_id=chain_id)
        self._wait_tasks_execution()
        contract = await Contract.get_contract(HexBytes(contract_address), chain_id)
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # After reset cache and database retries should download the contract
        contract.fetch_retries = 0
        await redis.delete(cache_key)
        await contract.update()
        get_contract_metadata_task.send(address=contract_address, chain_id=chain_id)
        self._wait_tasks_execution()
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
        etherscan_get_contract_metadata_mock.side_effect = [
            etherscan_proxy_metadata_mock,
            etherscan_metadata_mock,
        ]
        contract_address = Account.create().address
        proxy_implementation_address = "0x43506849D7C04F9138D1A2050bbF3A0c054402dd"
        chain_id = 1

        get_contract_metadata_task.send(address=contract_address, chain_id=chain_id)

        self._wait_tasks_execution()

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

        create_safe_contracts_task_for_new_chains.send(chain_id=new_chain_id)
        self._wait_tasks_execution()

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

    @mock.patch.object(ContractMetadataService, "enabled_clients")
    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @db_session_context
    async def test_proxy_selector_cache_invalidated_when_implementation_abi_downloaded(
        self,
        etherscan_get_contract_metadata_mock: MagicMock,
        mock_enabled_clients: MagicMock,
    ):
        """
        Regression: proxy selector cache must be invalidated when the implementation ABI
        is downloaded for the first time, so the next decode uses the implementation ABI.
        """
        chain_id = 1
        proxy_address = Account.create().address
        impl_address = Account.create().address

        source = AbiSource(name="Etherscan", url="")
        await source.create()

        proxy_abi_obj = Abi(
            abi_hash=b"ProxyABI",
            abi_json=example_abi,
            relevance=1,
            source_id=source.id,
        )
        await proxy_abi_obj.create()

        # Proxy has its own ABI and an implementation pointer; impl has no ABI yet.
        proxy_contract = Contract(
            address=HexBytes(proxy_address),
            abi=proxy_abi_obj,
            name="Proxy",
            chain_id=chain_id,
            implementation=HexBytes(impl_address),
        )
        await proxy_contract.create()
        impl_contract = Contract(
            address=HexBytes(impl_address),
            chain_id=chain_id,
        )
        await impl_contract.create()

        example_data = (
            Web3()
            .eth.contract(abi=example_abi)
            .functions.buyDroid(4, 10)
            .build_transaction(
                get_empty_tx_params() | {"to": NULL_ADDRESS, "chainId": chain_id}
            )["data"]
        )

        # First decode: impl has no ABI → falls back to proxy ABI → selector cache populated.
        decoder = DataDecoderService()
        await decoder.init()
        fn_name, arguments = await decoder.decode_transaction(
            example_data, address=Address(HexBytes(proxy_address)), chain_id=chain_id
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, {"droidId": "4", "numberOfDroids": "10"})

        redis = get_redis()
        hash_key = get_key_for_contract_selectors(proxy_address)
        field_key = get_field_key_for_selectors(chain_id)
        self.assertTrue(await redis.hexists(hash_key, field_key))  # type: ignore[misc]

        # Task downloads the implementation ABI (swapped param names).
        impl_metadata = ContractMetadata("Implementation", example_swapped_abi, False)  # type: ignore[arg-type]
        etherscan_get_contract_metadata_mock.return_value = impl_metadata
        mock_enabled_clients.return_value = [
            AsyncEtherscanClientV2(EthereumNetwork(chain_id))
        ]
        get_proxy_implementation_metadata_task.send(
            proxy_address=proxy_address,
            implementation_address=impl_address,
            chain_id=chain_id,
        )
        self._wait_tasks_execution()

        # Impl ABI must now be stored.
        await db_session.refresh(impl_contract)
        impl_contract_updated = await Contract.get_contract(
            HexBytes(impl_address), chain_id
        )
        self.assertIsNotNone(impl_contract_updated.abi_id)

        # Proxy selector cache must have been cleared.
        self.assertFalse(await redis.hexists(hash_key, field_key))  # type: ignore[misc]

        # Second decode (fresh decoder to bypass alru_cache): must use implementation ABI.
        decoder2 = DataDecoderService()
        await decoder2.init()
        fn_name, arguments = await decoder2.decode_transaction(
            example_data, address=Address(HexBytes(proxy_address)), chain_id=chain_id
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(
            arguments,
            {"numberOfDroids": "4", "droidId": "10"},
            "Proxy decoding should use implementation ABI after its download",
        )

    @db_session_context
    async def test_create_safe_contracts_task_with_lock_held(self):
        new_chain_id = 888
        lock_key = f"lock:create_safe_contracts:{new_chain_id}"
        redis = get_redis()

        await redis.set(lock_key, "1", ex=300)

        create_safe_contracts_task_for_new_chains.send(chain_id=new_chain_id)
        self._wait_tasks_execution()

        contracts = await Contract.get_all()
        chain_contracts = [c for c in contracts if c.chain_id == new_chain_id]
        self.assertEqual(len(chain_contracts), 0)

        await redis.delete(lock_key)
