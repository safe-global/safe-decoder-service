import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.config import settings
from app.workers.tasks import example_task


class QueueConsumer:

    @staticmethod
    async def process_incoming_message(message: AbstractIncomingMessage) -> None:
        await message.ack()
        body = message.body
        if body:
            example_task.send(body.decode())

    async def consume(self, loop):
        connection = await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, loop=loop
        )
        channel = await connection.channel()
        queue = await channel.declare_queue(settings.RABBITMQ_QUEUE_NAME)
        await queue.consume(self.process_incoming_message, no_ack=False)
        return connection
