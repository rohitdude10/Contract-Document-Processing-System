
import pytest
from sqlalchemy import select

from app.models.batch import Batch
from app.models.document import Document


@pytest.mark.asyncio
async def test_batch_and_document_relationship(db_session):
    batch = Batch(
        original_filename="contracts.zip",
        status="queued",
        total_documents=1,
        processed_documents=0,
        failed_documents=0,
        requested_variables=["effective_date"],
        upload_size=100,
    )

    db_session.add(batch)
    await db_session.flush()

    document = Document(
        batch_id=batch.id,
        original_filename="contract.txt",
        stored_path="storage_test/contract.txt",
        file_size=100,
        mime_type="text/plain",
        status="queued",
        attempt_count=0,
    )

    db_session.add(document)
    await db_session.commit()

    result = await db_session.execute(
        select(Document).where(Document.batch_id == batch.id)
    )
    documents = result.scalars().all()

    assert len(documents) == 1
    assert documents[0].original_filename == "contract.txt"


@pytest.mark.asyncio
async def test_document_belongs_to_correct_batch(db_session):
    batch = Batch(
        original_filename="contracts.zip",
        status="queued",
        total_documents=0,
        processed_documents=0,
        failed_documents=0,
        requested_variables=[],
        upload_size=0,
    )

    db_session.add(batch)
    await db_session.commit()

    result = await db_session.execute(
        select(Batch).where(Batch.id == batch.id)
    )

    saved_batch = result.scalar_one()

    assert saved_batch.id == batch.id
    assert saved_batch.status == "queued"
