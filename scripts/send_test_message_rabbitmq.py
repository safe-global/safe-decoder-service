import random

import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", port=5672),
)
channel = connection.channel()
channel.queue_declare(queue="default")
channel.basic_publish(
    exchange="", routing_key="default", body=f"message with ID-{random.randint(1, 100)}"
)
