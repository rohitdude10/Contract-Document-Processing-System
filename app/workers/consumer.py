
import asyncio
import json
import logging
from uuid import UUID

import aio_pika
from sqlalchemy import func, select

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Batch, Document
from app.workers.connection import rabbitmq
from app.workers.tasks import process_document, utc_now

logger = logging.getLogger(__name__)


async def mark_document_failed(document_id: UUID, batch_id: UUID):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Document)
                .where(Document.id == document_id)
                .with_for_update()
            )

            document = result.scalar_one_or_none()

            if document is None or document.status == "completed":
                return

            document.status = "failed"

            batch = await session.get(Batch, batch_id)

            if batch is None:
                return

            completed_count = await session.scalar(
                select(func.count(Document.id)).where(
                    Document.batch_id == batch_id,
                    Document.status == "completed",
                )
            )

            failed_count = await session.scalar(
                select(func.count(Document.id)).where(
                    Document.batch_id == batch_id,
                    Document.status == "failed",
                )
            )

            batch.processed_documents = completed_count or 0
            batch.failed_documents = failed_count or 0

            finished = (
                batch.processed_documents
                + batch.failed_documents
            )

            if finished < batch.total_documents:
                batch.status = "processing"
            elif batch.failed_documents == batch.total_documents:
                batch.status = "failed"
            elif batch.failed_documents:
                batch.status = "partially_completed"
            else:
                batch.status = "completed"


async def publish_retry(message, retry_count: int):
    headers = dict(message.headers or {})
    headers["retry_count"] = retry_count

    retry_message = aio_pika.Message(
        body=message.body,
        headers=headers,
        content_type=message.content_type,
        message_id=message.message_id,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await rabbitmq.exchange.publish(
        retry_message,
        routing_key=settings.RABBITMQ_RETRY_QUEUE,
        mandatory=True,
    )


async def publish_to_dlq(message, error: Exception):
    headers = dict(message.headers or {})
    headers["failure_reason"] = str(error)[:1000]

    dlq_message = aio_pika.Message(
        body=message.body,
        headers=headers,
        content_type=message.content_type,
        message_id=message.message_id,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await rabbitmq.exchange.publish(
        dlq_message,
        routing_key=settings.RABBITMQ_DLQ,
        mandatory=True,
    )


async def handle_message(message: aio_pika.IncomingMessage):
    try:
        payload = json.loads(message.body.decode("utf-8"))

        batch_id = UUID(payload["batch_id"])
        document_id = UUID(payload["document_id"])

        retry_count = int(
            (message.headers or {}).get("retry_count", 0)
        )

        logger.info(
            "Received document task: document_id=%s retry=%s",
            document_id,
            retry_count,
        )

        await process_document(
            batch_id=batch_id,
            document_id=document_id,
        )

        await message.ack()

    except Exception as exc:
        logger.exception("Document task failed")

        try:
            payload = json.loads(message.body.decode("utf-8"))
            batch_id = UUID(payload["batch_id"])
            document_id = UUID(payload["document_id"])

            retry_count = int(
                (message.headers or {}).get("retry_count", 0)
            )

            if retry_count < settings.RABBITMQ_MAX_RETRIES:
                await publish_retry(
                    message,
                    retry_count + 1,
                )

                logger.warning(
                    "Scheduled retry %s for document %s",
                    retry_count + 1,
                    document_id,
                )

            else:
                await mark_document_failed(
                    document_id,
                    batch_id,
                )

                await publish_to_dlq(message, exc)

                logger.error(
                    "Document moved to DLQ: %s",
                    document_id,
                )

            # Acknowledge only after the replacement message
            # has been successfully published.
            await message.ack()

        except Exception:
            logger.exception(
                "Could not schedule retry or DLQ message. "
                "Rejecting without requeue."
            )
            # Requeue if publishing failed so RabbitMQ can
            # redeliver the original message.
            await message.nack(requeue=True)


async def start_consumer():
    await rabbitmq.connect()

    queue = await rabbitmq.channel.get_queue(
        settings.RABBITMQ_MAIN_QUEUE
    )

    logger.info(
        "Worker listening on queue: %s",
        settings.RABBITMQ_MAIN_QUEUE,
    )

    await queue.consume(
        handle_message,
        no_ack=False,
    )

    # Keep the worker process alive.
    await asyncio.Future()
