
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.review import (
    DocumentReviewStatistics,
    FindingResponse,
    ReviewRequest,
    ReviewStatistics,
)
from app.services.review_service import (
    FindingNotFoundError,
    InvalidReviewTransitionError,
    get_batch_review_statistics,
    get_document_review_statistics,
    list_batch_findings,
    list_document_findings,
    review_finding,
)

router = APIRouter(tags=["Human Review"])


@router.get(
    "/documents/{document_id}/findings",
    response_model=list[FindingResponse],
)
async def get_document_findings(
    document_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_document_findings(
            session=db,
            document_id=document_id,
            offset=offset,
            limit=limit,
        )
    except FindingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/batches/{batch_id}/findings",
    response_model=list[FindingResponse],
)
async def get_batch_findings(
    batch_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_batch_findings(
            session=db,
            batch_id=batch_id,
            offset=offset,
            limit=limit,
        )
    except FindingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "/findings/{finding_id}/review",
    response_model=FindingResponse,
)
async def review_finding_endpoint(
    finding_id: UUID,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await review_finding(
            session=db,
            finding_id=finding_id,
            request=request,
        )

    except FindingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except InvalidReviewTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "/batches/{batch_id}/review-summary",
    response_model=ReviewStatistics,
)
async def get_batch_review_summary(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    summary = await get_batch_review_statistics(db, batch_id)

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    return summary


@router.get(
    "/documents/{document_id}/review-summary",
    response_model=DocumentReviewStatistics,
)
async def get_document_review_summary(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    summary = await get_document_review_statistics(
        db,
        document_id,
    )

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return summary
