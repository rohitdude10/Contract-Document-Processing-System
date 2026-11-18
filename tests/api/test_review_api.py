
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.batch import Batch
from app.models.document import Document
from app.models.finding import Finding


async def create_finding(db_session, status="pending"):
    batch = Batch(
        id=uuid4(),
        original_filename="contracts.zip",
        status="completed",
        total_documents=1,
        processed_documents=1,
        failed_documents=0,
        requested_variables=["effective_date"],
        upload_size=100,
    )
    db_session.add(batch)
    await db_session.flush()

    document = Document(
        id=uuid4(),
        batch_id=batch.id,
        original_filename="contract.txt",
        stored_path="storage_test/contract.txt",
        file_size=100,
        mime_type="text/plain",
        status="completed",
        attempt_count=1,
    )
    db_session.add(document)
    await db_session.flush()

    finding = Finding(
        id=uuid4(),
        document_id=document.id,
        variable_name="effective_date",
        extracted_value="2026-01-01",
        status=status,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    await db_session.commit()

    return batch, document, finding


@pytest.mark.asyncio
async def test_accept_finding(client, db_session):
    _, _, finding = await create_finding(db_session)

    response = await client.patch(
        f"/api/v1/findings/{finding.id}/review",
        json={
            "status": "accepted",
            "reviewed_by": "reviewer@example.com",
            "reviewer_comment": "Verified against the contract.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert response.json()["reviewed_by"] == "reviewer@example.com"


@pytest.mark.asyncio
async def test_reject_finding(client, db_session):
    _, _, finding = await create_finding(db_session)

    response = await client.patch(
        f"/api/v1/findings/{finding.id}/review",
        json={
            "status": "rejected",
            "reviewed_by": "reviewer@example.com",
            "reviewer_comment": "Incorrect extraction.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_cannot_review_finding_twice(client, db_session):
    _, _, finding = await create_finding(db_session)

    first = await client.patch(
        f"/api/v1/findings/{finding.id}/review",
        json={
            "status": "accepted",
            "reviewed_by": "reviewer@example.com",
        },
    )
    assert first.status_code == 200

    second = await client.patch(
        f"/api/v1/findings/{finding.id}/review",
        json={
            "status": "rejected",
            "reviewed_by": "reviewer@example.com",
        },
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_review_nonexistent_finding_returns_404(client):
    response = await client.patch(
        f"/api/v1/findings/{uuid4()}/review",
        json={
            "status": "accepted",
            "reviewed_by": "reviewer@example.com",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_review_status_returns_422(client, db_session):
    _, _, finding = await create_finding(db_session)

    response = await client.patch(
        f"/api/v1/findings/{finding.id}/review",
        json={
            "status": "pending",
            "reviewed_by": "reviewer@example.com",
        },
    )

    assert response.status_code == 422



@pytest.mark.asyncio
async def test_findings_can_be_reviewed_independently(
    client,
    db_session,
):
    batch, document, first = await create_finding(db_session)

    second = Finding(
        id=uuid4(),
        document_id=document.id,
        variable_name="expiry_date",
        extracted_value="2027-01-01",
        status="pending",
    )
    db_session.add(second)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/findings/{first.id}/review",
        json={
            "status": "accepted",
            "reviewed_by": "reviewer@example.com",
        },
    )

    assert response.status_code == 200

    await db_session.refresh(second)
    assert second.status == "pending"
