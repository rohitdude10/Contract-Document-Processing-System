
import asyncio
import pytest
from sqlalchemy import select, func

from app.models.finding import Finding
from app.workers.tasks import process_document


@pytest.mark.asyncio
async def test_duplicate_processing_does_not_duplicate_findings(
    db_session,
    seeded_document,
):
    batch_id, document_id = seeded_document

    await asyncio.gather(
        process_document(batch_id, document_id),
        process_document(batch_id, document_id),
    )

    result = await db_session.execute(
        select(func.count(Finding.id)).where(
            Finding.document_id == document_id
        )
    )

    finding_count = result.scalar_one()

    # One finding per requested variable.
    assert finding_count == 1
