
import json

import aio_pika
import pytest


@pytest.mark.asyncio
async def test_rabbitmq_publish_and_consume(rabbitmq_connection):
    channel = await rabbitmq_connection.channel()

    queue_name = "test.document.processing"

    queue = await channel.declare_queue(
        queue_name,
        durable=False,
        exclusive=True,
        auto_delete=True,
    )

    payload = {
        "batch_id": "11111111-1111-1111-1111-111111111111",
        "document_id": "22222222-2222-2222-2222-222222222222",
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=queue_name,
    )

    message = await queue.get(timeout=5, fail=True)

    received = json.loads(message.body)

    assert received["batch_id"] == payload["batch_id"]
    assert received["document_id"] == payload["document_id"]

    await message.ack()
    await channel.close()
