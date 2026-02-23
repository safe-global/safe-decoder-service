# SPDX-License-Identifier: FSL-1.1-MIT
import logging
from asyncio import AbstractEventLoop
from collections.abc import Callable
from typing import Any

import aio_pika
from aio_pika.abc import (
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
    ConsumerTag,
    ExchangeType,
)

from app.config import settings

from .exceptions import (
    QueueProviderNotConnectedException,
    QueueProviderUnableToConnectException,
)

logger = logging.getLogger(__name__)


class QueueProvider:
    _connection: AbstractRobustConnection | None
    _exchange: AbstractExchange | None
    _events_queue: AbstractQueue | None

    def __init__(self) -> None:
        """
        Initializes the QueueProvider instance with default values.
        """
        self._connection = None
        self._exchange = None
        self._events_queue = None

    async def _connect(self, loop: AbstractEventLoop) -> None:
        """
        Establishes a connection to RabbitMQ and sets up the exchange and queue.

        :param loop: The asyncio event loop used for the connection.
        :return:
        """
        try:
            logger.info("Connecting to RabbitMQ")
            self._connection = await aio_pika.connect_robust(
                url=settings.RABBITMQ_AMQP_URL, loop=loop
            )
            logger.info("Connected to RabbitMQ")
        except aio_pika.exceptions.AMQPConnectionError as e:
            raise QueueProviderUnableToConnectException from e

        channel = await self._connection.channel()
        self._exchange = await channel.declare_exchange(
            settings.RABBITMQ_AMQP_EXCHANGE, ExchangeType.FANOUT, durable=True
        )
        logger.info("Connected to %s exchange", settings.RABBITMQ_AMQP_EXCHANGE)
        self._events_queue = await channel.declare_queue(
            settings.RABBITMQ_DECODER_EVENTS_QUEUE_NAME, durable=True
        )
        if self._events_queue:
            await self._events_queue.bind(self._exchange)
        logger.info(
            "Reading from %s queue", settings.RABBITMQ_DECODER_EVENTS_QUEUE_NAME
        )

    async def connect(self, loop: AbstractEventLoop) -> None:
        """
        Ensures that the RabbitMQ connection is established.

        :param loop: The asyncio event loop used to establish the connection.
        :return:
        """
        if not self._connection:
            await self._connect(loop)

    def is_connected(self) -> bool:
        """
        Verifies if the connection to RabbitMQ is established.

        :return: True` if the connection is established, `False` otherwise.
        """
        return self._connection is not None

    async def disconnect(self) -> None:
        """
        Safely closes the RabbitMQ connection and cleans up resources.

        :return:
        """
        if self._connection:
            await self._connection.close()
            self._exchange = None
            self._connection = None
            self._events_queue = None

    async def consume(self, callback: Callable[[str], Any]) -> ConsumerTag:
        """
        Starts consuming messages from the declared queue.

        - Each message is processed using the provided callback function.

        :param callback: A function to process incoming messages.
        :return: A tag identifying the active consumer.
        :raises QueueProviderNotConnectedException: if no connection or queue is initialized.
        """
        if not self._connection or not self._events_queue:
            raise QueueProviderNotConnectedException()

        async def wrapped_callback(message: AbstractIncomingMessage) -> None:
            """
            Wrapper for processing the message and handling ACKs.

            :param message: The incoming RabbitMQ message.
            """
            body = message.body
            try:
                if body:
                    await callback(body.decode("utf-8"))
            except Exception:
                logger.exception("Error processing message with body: %s", body)
            finally:
                await message.ack()

        return await self._events_queue.consume(wrapped_callback)
