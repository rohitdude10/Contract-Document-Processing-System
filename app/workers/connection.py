
import aio_pika

from app.config import settings


class RabbitMQConnection:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            return

        self.connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL
        )

        self.channel = await self.connection.channel(
            publisher_confirms=True
        )

        await self.channel.set_qos(
            prefetch_count=settings.WORKER_PREFETCH_COUNT
        )

        self.exchange = await self.channel.declare_exchange(
            settings.RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # Main queue
        main_queue = await self.channel.declare_queue(
            settings.RABBITMQ_MAIN_QUEUE,
            durable=True,
        )

        await main_queue.bind(
            self.exchange,
            routing_key=settings.RABBITMQ_MAIN_QUEUE,
        )

        # Retry queue: messages expire and return to main queue.
        retry_queue = await self.channel.declare_queue(
            settings.RABBITMQ_RETRY_QUEUE,
            durable=True,
            arguments={
                "x-message-ttl": settings.RABBITMQ_RETRY_DELAY_MS,
                "x-dead-letter-exchange": settings.RABBITMQ_EXCHANGE,
                "x-dead-letter-routing-key": settings.RABBITMQ_MAIN_QUEUE,
            },
        )

        await retry_queue.bind(
            self.exchange,
            routing_key=settings.RABBITMQ_RETRY_QUEUE,
        )

        # Dead-letter queue for messages that exceed retry limit.
        dlq = await self.channel.declare_queue(
            settings.RABBITMQ_DLQ,
            durable=True,
        )

        await dlq.bind(
            self.exchange,
            routing_key=settings.RABBITMQ_DLQ,
        )

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


rabbitmq = RabbitMQConnection()
