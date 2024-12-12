import asyncio
import unittest
from unittest.mock import patch

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.config import settings
from app.datasources.queue.queue_provider import (
    QueueProvider,
    QueueProviderUnableToConnectException,
)


class TestQueueProviderIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.provider = QueueProvider()
        self.loop = asyncio.get_event_loop()

    async def test_connect_success(self):
        self.assertFalse(self.provider.is_connected())
        await self.provider.connect(self.loop)
        self.assertTrue(self.provider.is_connected())
        await self.provider.disconnect()
        self.assertFalse(self.provider.is_connected())

    async def test_connect_failure(self):
        provider = QueueProvider()

        with patch("app.config.settings.RABBITMQ_AMPQ_URL", "amqp://invalid-url"):
            with self.assertRaises(QueueProviderUnableToConnectException):
                await provider.connect(self.loop)

    async def test_consume(self):
        await self.provider.connect(self.loop)
        assert isinstance(self.provider._connection, AbstractRobustConnection)
        message = "Test message"
        channel = await self.provider._connection.channel()
        exchange = await channel.declare_exchange(
            settings.RABBITMQ_AMQP_EXCHANGE, aio_pika.ExchangeType.FANOUT
        )

        await exchange.publish(
            aio_pika.Message(body=message.encode("utf-8")),
            routing_key="",
        )

        received_messages = []

        def callback(message: str):
            received_messages.append(message)

        await self.provider.consume(callback)

        # Wait to make sure the message is consumed.
        await asyncio.sleep(1)

        self.assertIn(message, received_messages)
        await self.provider.disconnect()
