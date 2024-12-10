import json
import unittest
from typing import Any, Awaitable

from dramatiq.worker import Worker

from app.workers.tasks import redis_broker, test_task


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
