
import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.config import settings


logger = logging.getLogger(__name__)

rabbitmq_connection: AbstractRobustConnection | None = None


async def connect_rabbitmq():
    global rabbitmq_connection

    try:
        rabbitmq_connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            timeout=5,
        )

        logger.info("RabbitMQ connection established")

    except Exception:
        logger.exception("Failed to connect to RabbitMQ")
        rabbitmq_connection = None


async def check_rabbitmq_connection() -> bool:
    return (
        rabbitmq_connection is not None
        and not rabbitmq_connection.is_closed
    )


async def close_rabbitmq_connection():
    global rabbitmq_connection

    if rabbitmq_connection is not None:
        if not rabbitmq_connection.is_closed:
            await rabbitmq_connection.close()

        rabbitmq_connection = None
