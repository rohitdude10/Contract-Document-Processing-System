
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Batch, Document, Finding
from app.schemas.review import (
    DocumentReviewStatistics,
    FindingResponse,
    ReviewRequest,
    ReviewStatistics,
)


class FindingNotFoundError(Exception):
    pass


class InvalidReviewTransitionError(Exception):
    pass


def calculate_progress(reviewed: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round((reviewed / total) * 100, 2)


async def list_document_findings(
    session: AsyncSession,
    document_id: UUID,
    offset: int = 0,
    limit: int = 50,
):
    document_exists = await session.scalar(
        select(Document.id).where(Document.id == document_id)
    )

    if document_exists is None:
        raise FindingNotFoundError("Document not found")

    result = await session.execute(
        select(Finding)
        .where(Finding.document_id == document_id)
        .order_by(Finding.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    return [
        FindingResponse.model_validate(finding)
        for finding in result.scalars().all()
    ]


async def list_batch_findings(
    session: AsyncSession,
    batch_id: UUID,
    offset: int = 0,
    limit: int = 50,
):
    batch_exists = await session.scalar(
        select(Batch.id).where(Batch.id == batch_id)
    )

    if batch_exists is None:
        raise FindingNotFoundError("Batch not found")

    result = await session.execute(
        select(Finding)
        .join(Document, Finding.document_id == Document.id)
        .where(Document.batch_id == batch_id)
        .order_by(Finding.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    return [
        FindingResponse.model_validate(finding)
        for finding in result.scalars().all()
    ]


async def review_finding(
    session: AsyncSession,
    finding_id: UUID,
    request: ReviewRequest,
) -> FindingResponse:

    async with session.begin():
        result = await session.execute(
            select(Finding)
            .where(Finding.id == finding_id)
            .with_for_update()
        )

        finding = result.scalar_one_or_none()

        if finding is None:
            raise FindingNotFoundError("Finding not found")

        if finding.status != "pending":
            raise InvalidReviewTransitionError(
                f"Cannot review a finding with status "
                f"'{finding.status}'. Only pending findings "
                f"can be reviewed."
            )

        finding.status = request.status
        finding.reviewer_comment = request.reviewer_comment
        finding.reviewed_by = request.reviewed_by
        finding.reviewed_at = datetime.now(timezone.utc)

        await session.flush()

    await session.refresh(finding)

    return FindingResponse.model_validate(finding)


async def get_batch_review_statistics(
    session: AsyncSession,
    batch_id: UUID,
) -> ReviewStatistics | None:

    batch_exists = await session.scalar(
        select(Batch.id).where(Batch.id == batch_id)
    )

    if batch_exists is None:
        return None

    result = await session.execute(
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

    row = result.one()

    total = row.total or 0
    pending = row.pending or 0
    accepted = row.accepted or 0
    rejected = row.rejected or 0
    reviewed = accepted + rejected

    return ReviewStatistics(
        batch_id=batch_id,
        total_findings=total,
        pending_findings=pending,
        accepted_findings=accepted,
        rejected_findings=rejected,
        reviewed_findings=reviewed,
        review_progress=calculate_progress(reviewed, total),
    )


async def get_document_review_statistics(
    session: AsyncSession,
    document_id: UUID,
) -> DocumentReviewStatistics | None:

    document_exists = await session.scalar(
        select(Document.id).where(Document.id == document_id)
    )

    if document_exists is None:
        return None

    result = await session.execute(
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
        ).where(Finding.document_id == document_id)
    )

    row = result.one()

    total = row.total or 0
    pending = row.pending or 0
    accepted = row.accepted or 0
    rejected = row.rejected or 0
    reviewed = accepted + rejected

    return DocumentReviewStatistics(
        document_id=document_id,
        total_findings=total,
        pending_findings=pending,
        accepted_findings=accepted,
        rejected_findings=rejected,
        reviewed_findings=reviewed,
        review_progress=calculate_progress(reviewed, total),
    )
