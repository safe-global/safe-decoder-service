import json
import unittest
from typing import Any, Awaitable

from dramatiq.worker import Worker
from hexbytes import HexBytes
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Contract
from app.workers.tasks import get_contract_metadata_task, redis_broker, test_task

from ..datasources.db.db_async_conn import DbAsyncConn


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

    @database_session
    async def test_get_contract_metadata_task(self, session: AsyncSession):
        contract_address = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"
        chain_id = 100
        get_contract_metadata_task.fn(contract_address, chain_id)
        contract = await Contract.get_contract(
            session, HexBytes(contract_address), chain_id
        )
        self.assertIsNotNone(contract)
