
import pytest
from sqlalchemy import select

from app.models.batch import Batch
from app.models.document import Document
from app.models.finding import Finding
from app.schemas.review import ReviewRequest
from app.services.review_service import (
    get_batch_review_statistics,
    review_finding,
)
from app.workers import tasks
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_complete_batch_processing_workflow(
    db_session,
    tmp_path,
    monkeypatch,
):
    """
    End-to-end workflow:

    1. Create a batch.
    2. Add two documents.
    3. Process both documents using the worker.
    4. Verify findings are persisted.
    5. Review one finding.
    6. Verify review statistics.
    """

    # --------------------------------------------------
    # STEP 1: Configure worker to use the test database
    # --------------------------------------------------

    # process_document creates its own database sessions.
    # Make those sessions use the same test database.
    monkeypatch.setattr(
        tasks,
        "AsyncSessionLocal",
        TestSessionLocal,
    )

    # --------------------------------------------------
    # STEP 2: Create sample contract files
    # --------------------------------------------------

    document_1_path = tmp_path / "contract_1.txt"
    document_2_path = tmp_path / "contract_2.txt"

    document_1_path.write_text(
        "Contract 1. Effective date: 2026-01-01.",
        encoding="utf-8",
    )

    document_2_path.write_text(
        "Contract 2. Effective date: 2026-02-01.",
        encoding="utf-8",
    )

    # --------------------------------------------------
    # STEP 3: Create batch in PostgreSQL
    # --------------------------------------------------

    batch = Batch(
        original_filename="contracts.zip",
        status="queued",
        total_documents=2,
        processed_documents=0,
        failed_documents=0,
        requested_variables=[
            "effective_date",
            "expiry_date",
        ],
        upload_size=200,
    )

    db_session.add(batch)
    await db_session.flush()

    # --------------------------------------------------
    # STEP 4: Create documents
    # --------------------------------------------------

    document_1 = Document(
        batch_id=batch.id,
        original_filename="contract_1.txt",
        stored_path=str(document_1_path),
        file_size=document_1_path.stat().st_size,
        mime_type="text/plain",
        status="queued",
        attempt_count=0,
    )

    document_2 = Document(
        batch_id=batch.id,
        original_filename="contract_2.txt",
        stored_path=str(document_2_path),
        file_size=document_2_path.stat().st_size,
        mime_type="text/plain",
        status="queued",
        attempt_count=0,
    )

    db_session.add_all([document_1, document_2])
    await db_session.commit()

    batch_id = batch.id
    document_1_id = document_1.id
    document_2_id = document_2.id

    # --------------------------------------------------
    # STEP 5: Process documents through the worker
    # --------------------------------------------------

    await tasks.process_document(
        batch_id=batch_id,
        document_id=document_1_id,
    )

    await tasks.process_document(
        batch_id=batch_id,
        document_id=document_2_id,
    )

    # --------------------------------------------------
    # STEP 6: Verify document processing results
    # --------------------------------------------------

    await db_session.refresh(batch)
    await db_session.refresh(document_1)
    await db_session.refresh(document_2)

    assert document_1.status == "completed"
    assert document_2.status == "completed"

    assert batch.total_documents == 2
    assert batch.processed_documents == 2
    assert batch.failed_documents == 0

    # --------------------------------------------------
    # STEP 7: Verify findings were persisted
    # --------------------------------------------------

    result = await db_session.execute(
        select(Finding).where(
            Finding.document_id.in_([
                document_1_id,
                document_2_id,
            ])
        )
    )

    findings = result.scalars().all()

    # Two requested variables per document.
    assert len(findings) == 4

    document_1_findings = [
        finding
        for finding in findings
        if finding.document_id == document_1_id
    ]

    document_2_findings = [
        finding
        for finding in findings
        if finding.document_id == document_2_id
    ]

    assert len(document_1_findings) == 2
    assert len(document_2_findings) == 2

    assert all(
        finding.status == "pending"
        for finding in findings
    )

    # --------------------------------------------------
    # STEP 8: Accept one finding
    # --------------------------------------------------

    finding_to_review = document_1_findings[0]

    review_request = ReviewRequest(
        status="accepted",
        reviewed_by="integration-test-reviewer",
        reviewer_comment="Verified during integration test.",
    )

    async with TestSessionLocal() as review_session:
        await review_finding(
            review_session,
            finding_to_review.id,
            review_request,
        )

    # --------------------------------------------------
    # STEP 9: Verify independent review
    # --------------------------------------------------

    await db_session.refresh(finding_to_review)

    assert finding_to_review.status == "accepted"

    # Other findings must remain pending.
    for finding in findings:
        if finding.id != finding_to_review.id:
            await db_session.refresh(finding)
            assert finding.status == "pending"

    # --------------------------------------------------
    # STEP 10: Verify batch review statistics
    # --------------------------------------------------

    summary = await get_batch_review_statistics(
        db_session,
        batch_id,
    )

    assert summary.total_findings == 4
    assert summary.accepted_findings == 1
    assert summary.rejected_findings == 0
    assert summary.pending_findings == 3
    assert summary.reviewed_findings == 1
    assert summary.review_progress == 25.0
