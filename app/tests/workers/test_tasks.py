import json
import unittest
from typing import Any, Awaitable
from unittest import mock
from unittest.mock import MagicMock

from dramatiq.worker import Worker
from eth_account import Account
from hexbytes import HexBytes
from safe_eth.eth import EthereumNetwork
from safe_eth.eth.clients import AsyncEtherscanClientV2
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import AbiSource, Contract
from app.workers.tasks import get_contract_metadata_task, redis_broker, test_task

from ...datasources.cache.redis import get_redis
from ...services.contract_metadata_service import ContractMetadataService
from ..datasources.db.db_async_conn import DbAsyncConn
from ..mocks.contract_metadata_mocks import (
    etherscan_metadata_mock,
    etherscan_proxy_metadata_mock,
)


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
        test_task.send(test_message)

        redis_tasks = redis_broker.client.lrange("dramatiq:default", 0, -1)
        assert isinstance(redis_tasks, list)
        self.assertEqual(len(redis_tasks), 1)
        task_id = redis_tasks[0]
        task_info_raw: Any = redis_broker.client.hget("dramatiq:default.msgs", task_id)
        assert isinstance(task_info_raw, bytes)
        task_info = json.loads(task_info_raw)
        self.assertEqual(task_info.get("args"), [test_message])
        self.assertEqual(task_info.get("actor_name"), "test_task")

        self.worker.start()

        redis_tasks = redis_broker.client.lrange("dramatiq:default", 0, -1)
        assert isinstance(redis_tasks, list)
        self.assertEqual(len(redis_tasks), 0)


class TestAsyncTasks(DbAsyncConn):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.worker = Worker(redis_broker)
        self.worker.start()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.worker.stop()
        redis = get_redis()
        redis.flushall()

    def _wait_tasks_execution(self):
        redis_tasks = self.worker.broker.client.lrange("dramatiq:default", 0, -1)
        while len(redis_tasks) > 0:
            redis_tasks = self.worker.broker.client.lrange("dramatiq:default", 0, -1)

    @mock.patch.object(ContractMetadataService, "enabled_clients")
    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @database_session
    async def test_get_contract_metadata_task(
        self,
        etherscan_get_contract_metadata_mock: MagicMock,
        mock_enabled_clients: MagicMock,
        session: AsyncSession,
    ):
        contract_address = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
        chain_id = 100
        cache_key = f"should_attempt_download:{contract_address}:{chain_id}:0"
        redis = get_redis()
        redis.delete(cache_key)
        await AbiSource(name="Etherscan", url="").create(session)
        etherscan_get_contract_metadata_mock.return_value = None
        mock_enabled_clients.return_value = [
            AsyncEtherscanClientV2(EthereumNetwork(chain_id))
        ]
        # Should try one time
        get_contract_metadata_task.fn(address=contract_address, chain_id=chain_id)
        contract = await Contract.get_contract(
            session, HexBytes(contract_address), chain_id
        )
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # Shouldn't try second time
        etherscan_get_contract_metadata_mock.return_value = etherscan_metadata_mock
        chain_id = 100
        get_contract_metadata_task.fn(address=contract_address, chain_id=chain_id)
        contract = await Contract.get_contract(
            session, HexBytes(contract_address), chain_id
        )
        self.assertIsNotNone(contract)
        self.assertIsNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 1)

        # After reset cache and database retries should download the contract
        contract.fetch_retries = 0
        redis.delete(cache_key)
        await contract.update(session)
        get_contract_metadata_task.fn(address=contract_address, chain_id=chain_id)
        await session.refresh(contract)
        contract = await Contract.get_contract(
            session, HexBytes(contract_address), chain_id
        )
        self.assertIsNotNone(contract)
        self.assertIsNotNone(contract.abi_id)
        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 2)

    @mock.patch.object(
        AsyncEtherscanClientV2, "async_get_contract_metadata", autospec=True
    )
    @database_session
    async def test_get_contract_metadata_task_with_proxy(
        self, etherscan_get_contract_metadata_mock: MagicMock, session: AsyncSession
    ):
        etherscan_get_contract_metadata_mock.side_effect = [
            etherscan_proxy_metadata_mock,
            etherscan_metadata_mock,
        ]
        contract_address = Account.create().address
        proxy_implementation_address = "0x43506849D7C04F9138D1A2050bbF3A0c054402dd"
        chain_id = 1

        get_contract_metadata_task.fn(address=contract_address, chain_id=chain_id)

        self._wait_tasks_execution()

        contract = await Contract.get_contract(
            session, HexBytes(contract_address), chain_id
        )
        self.assertIsNotNone(contract)

        proxy_implementation = await Contract.get_contract(
            session, HexBytes(proxy_implementation_address), chain_id
        )
        self.assertIsNotNone(proxy_implementation)

        self.assertEqual(etherscan_get_contract_metadata_mock.call_count, 2)
