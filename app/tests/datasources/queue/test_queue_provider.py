# SPDX-License-Identifier: FSL-1.1-MIT
import asyncio
import unittest
from unittest.mock import patch

import aio_pika

from app.datasources.queue.exceptions import QueueProviderUnableToConnectException
from app.datasources.queue.queue_provider import QueueProvider


class TestQueueProviderIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.provider = QueueProvider()
        self.loop = asyncio.get_event_loop()

    async def asyncTearDown(self):
        await self.provider.disconnect()

    async def test_connect_success(self):
        self.assertFalse(self.provider.is_connected())
        await self.provider.connect(self.loop)
        self.assertTrue(self.provider.is_connected())
        await self.provider.disconnect()
        self.assertFalse(self.provider.is_connected())

    async def test_connect_failure(self):
        provider = QueueProvider()

        with patch("app.config.settings.RABBITMQ_AMQP_URL", "amqp://invalid-url"):
            with self.assertRaises(QueueProviderUnableToConnectException):
                await provider.connect(self.loop)

    async def test_consume_only_bound_event_types(self):
        await self.provider.connect(self.loop)
        assert self.provider._exchange is not None
        assert self.provider._events_queue is not None
        await self.provider._events_queue.purge()
        # The last message is bound. RabbitMQ keeps the publish order inside a
        # queue, so once it is received any earlier message routed to the
        # queue was received too
        routing_keys = [
            "1.INCOMING_ETHER.0x5afe",
            "1.EXECUTED_MULTISIG_TRANSACTION.0x5afe",
            "1.PENDING_MULTISIG_TRANSACTION.0x5afe",
            "EXECUTED_MULTISIG_TRANSACTION",
            "100.EXECUTED_MULTISIG_TRANSACTION._",
        ]
        expected_messages = [
            "1.EXECUTED_MULTISIG_TRANSACTION.0x5afe",
            "100.EXECUTED_MULTISIG_TRANSACTION._",
        ]
        for routing_key in routing_keys:
            await self.provider._exchange.publish(
                aio_pika.Message(body=routing_key.encode("utf-8")),
                routing_key=routing_key,
            )

        received_messages: list[str] = []
        last_received = asyncio.Event()

        async def callback(message: str):
            received_messages.append(message)
            if message == expected_messages[-1]:
                last_received.set()

        await self.provider.consume(callback)
        await asyncio.wait_for(last_received.wait(), timeout=5)

        self.assertEqual(received_messages, expected_messages)
