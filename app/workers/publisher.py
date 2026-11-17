
import json
import logging
from uuid import UUID

import aio_pika

from app.config import settings
from app.workers.connection import rabbitmq

logger = logging.getLogger(__name__)


async def publish_document_task(
    batch_id: UUID,
    document_id: UUID,
) -> None:
    if rabbitmq.exchange is None:
        await rabbitmq.connect()

    payload = {
        "batch_id": str(batch_id),
        "document_id": str(document_id),
    }

    message = aio_pika.Message(
        body=json.dumps(payload).encode("utf-8"),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
        message_id=str(document_id),
        headers={"retry_count": 0},
    )

    await rabbitmq.exchange.publish(
        message,
        routing_key=settings.RABBITMQ_MAIN_QUEUE,
        mandatory=True,
    )

    logger.info(
        "Published document task: batch_id=%s document_id=%s",
        batch_id,
        document_id,
    )


async def publish_batch_tasks(batch_id, documents):
    for document in documents:
        await publish_document_task(
            batch_id=batch_id,
            document_id=document.id,
        )