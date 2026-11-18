
from io import BytesIO

import pytest

from tests.helpers.zip_factory import create_zip


@pytest.mark.asyncio
async def test_upload_valid_batch(client, monkeypatch, temp_storage):
    """
    Isolate the API test from RabbitMQ.
    The batch should be persisted even when publishing is stubbed.
    """
    from app.api.routes import batches

    async def fake_publish_batch_tasks(**kwargs):
        return None

    monkeypatch.setattr(
        batches,
        "publish_batch_tasks",
        fake_publish_batch_tasks,
    )

    archive = create_zip({
        "contract-1.txt": b"Sample contract one",
        "contract-2.txt": b"Sample contract two",
    })

    response = await client.post(
        "/api/v1/batches",
        files={
            "file": (
                "contracts.zip",
                BytesIO(archive),
                "application/zip",
            )
        },
        data={
            "requested_variables": (
                '{"variables": ["effective_date", "expiry_date"]}'
            )
        },
    )

    assert response.status_code in (200, 201), response.text

    body = response.json()
    assert body["total_documents"] == 2


@pytest.mark.asyncio
async def test_upload_rejects_invalid_zip(client, monkeypatch, temp_storage):
    from app.api.routes import batches

    async def fake_publish_batch_tasks(**kwargs):
        return None

    monkeypatch.setattr(
        batches,
        "publish_batch_tasks",
        fake_publish_batch_tasks,
    )

    response = await client.post(
        "/api/v1/batches",
        files={
            "file": (
                "invalid.zip",
                BytesIO(b"not a zip"),
                "application/zip",
            )
        },
        data={
            "requested_variables": '{"variables": ["effective_date"]}'
        },
    )

    assert response.status_code == 422
