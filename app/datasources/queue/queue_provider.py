from asyncio import AbstractEventLoop
from typing import Any, Callable

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


class QueueProviderException(Exception):
    """
    Generic exception for QueueProvider errors.
    """

    pass


class QueueProviderUnableToConnectException(QueueProviderException):
    """
    Raised when a connection to RabbitMQ cannot be established.
    """

    pass


class QueueProviderNotConnectedException(QueueProviderException):
    """
    Raised when no connection is established.
    """

    pass


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
            self._connection = await aio_pika.connect_robust(
                url=settings.RABBITMQ_AMPQ_URL, loop=loop
            )
        except aio_pika.exceptions.AMQPConnectionError as e:
            raise QueueProviderUnableToConnectException(e)

        channel = await self._connection.channel()
        self._exchange = await channel.declare_exchange(
            settings.RABBITMQ_AMQP_EXCHANGE, ExchangeType.FANOUT
        )
        self._events_queue = await channel.declare_queue(
            settings.RABBITMQ_DECODER_EVENTS_QUEUE_NAME, durable=True
        )
        if self._events_queue:
            await self._events_queue.bind(self._exchange)

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
            if self._events_queue and self._exchange:
                await self._events_queue.unbind(exchange=self._exchange)
                await self._events_queue.delete(if_unused=False, if_empty=False)
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
            await message.ack()
            body = message.body
            if body:
                callback(body.decode("utf-8"))

        return await self._events_queue.consume(wrapped_callback)