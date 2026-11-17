
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.models import Batch, Document, Finding
from app.schemas.tracking import (
    BatchDetail,
    BatchListItem,
    BatchSummary,
    DocumentDetail,
    DocumentListItem,
)


def percentage(completed: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round((completed / total) * 100, 2)


async def get_document_counts(session, batch_id: UUID) -> dict:
    result = await session.execute(
        select(
            func.count(Document.id).label("total"),
            func.count(
                case((Document.status == "queued", 1))
            ).label("queued"),
            func.count(
                case((Document.status == "processing", 1))
            ).label("processing"),
            func.count(
                case((Document.status == "completed", 1))
            ).label("completed"),
            func.count(
                case((Document.status == "failed", 1))
            ).label("failed"),
        ).where(Document.batch_id == batch_id)
    )

    row = result.one()

    return {
        "total": row.total or 0,
        "queued": row.queued or 0,
        "processing": row.processing or 0,
        "completed": row.completed or 0,
        "failed": row.failed or 0,
    }


async def get_batch_list_item(session, batch: Batch) -> BatchListItem:
    counts = await get_document_counts(session, batch.id)

    finished = counts["completed"] + counts["failed"]
    pending = counts["total"] - finished

    return BatchListItem(
        id=batch.id,
        original_filename=batch.original_filename,
        status=batch.status,
        total_documents=counts["total"],
        processed_documents=counts["completed"],
        failed_documents=counts["failed"],
        pending_documents=pending,
        processing_progress=percentage(finished, counts["total"]),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


async def list_batches(
    session,
    offset: int = 0,
    limit: int = 20,
) -> list[BatchListItem]:
    result = await session.execute(
        select(Batch)
        .order_by(Batch.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    batches = result.scalars().all()

    return [
        await get_batch_list_item(session, batch)
        for batch in batches
    ]


async def get_batch_details(
    session,
    batch_id: UUID,
) -> BatchDetail | None:
    result = await session.execute(
        select(Batch).where(Batch.id == batch_id)
    )

    batch = result.scalar_one_or_none()

    if batch is None:
        return None

    counts = await get_document_counts(session, batch_id)

    finished = counts["completed"] + counts["failed"]

    return BatchDetail(
        id=batch.id,
        original_filename=batch.original_filename,
        status=batch.status,
        total_documents=counts["total"],
        processed_documents=counts["completed"],
        failed_documents=counts["failed"],
        pending_documents=counts["total"] - finished,
        processing_progress=percentage(finished, counts["total"]),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        requested_variables=batch.requested_variables,
        upload_size=batch.upload_size,
    )


async def list_batch_documents(
    session,
    batch_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[DocumentListItem] | None:
    batch_exists = await session.scalar(
        select(Batch.id).where(Batch.id == batch_id)
    )

    if batch_exists is None:
        return None

    result = await session.execute(
        select(Document)
        .where(Document.batch_id == batch_id)
        .order_by(Document.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    return [
        DocumentListItem.model_validate(document)
        for document in result.scalars().all()
    ]


async def get_document_details(
    session,
    document_id: UUID,
) -> DocumentDetail | None:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.findings))
        .where(Document.id == document_id)
    )

    document = result.scalar_one_or_none()

    if document is None:
        return None

    return DocumentDetail.model_validate(document)


async def get_batch_summary(
    session,
    batch_id: UUID,
) -> BatchSummary | None:
    batch_exists = await session.scalar(
        select(Batch.id).where(Batch.id == batch_id)
    )

    if batch_exists is None:
        return None

    documents = await get_document_counts(session, batch_id)

    finding_result = await session.execute(
        select(
            func.count(Finding.id).label("total"),
            func.count(
                case((Finding.status == "pending", 1))
            ).label("pending"),
            func.count(
                case((Finding.status == "accepted", 1))
            ).label("accepted"),
            func.count(
                case((Finding.status == "rejected", 1))
            ).label("rejected"),
        )
        .join(Document, Finding.document_id == Document.id)
        .where(Document.batch_id == batch_id)
    )

    findings = finding_result.one()

    total_findings = findings.total or 0
    pending_findings = findings.pending or 0
    accepted_findings = findings.accepted or 0
    rejected_findings = findings.rejected or 0

    finished_documents = (
        documents["completed"] + documents["failed"]
    )

    reviewed_findings = accepted_findings + rejected_findings

    return BatchSummary(
        batch_id=batch_id,
        total_documents=documents["total"],
        queued_documents=documents["queued"],
        processing_documents=documents["processing"],
        completed_documents=documents["completed"],
        failed_documents=documents["failed"],
        pending_documents=(
            documents["total"] - finished_documents
        ),
        total_findings=total_findings,
        pending_findings=pending_findings,
        accepted_findings=accepted_findings,
        rejected_findings=rejected_findings,
        processing_progress=percentage(
            finished_documents,
            documents["total"],
        ),
        review_progress=percentage(
            reviewed_findings,
            total_findings,
        ),
    )

