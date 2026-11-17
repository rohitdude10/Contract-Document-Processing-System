
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.tracking import (
    BatchDetail,
    BatchListItem,
    BatchSummary,
    DocumentDetail,
    DocumentListItem,
)
from app.services.tracking_service import (
    get_batch_details,
    get_batch_summary,
    get_document_details,
    list_batch_documents,
    list_batches,
)

router = APIRouter(tags=["Batch Tracking"])


@router.get(
    "/batches",
    response_model=list[BatchListItem],
)
async def get_batches(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_batches(
        session=db,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/batches/{batch_id}",
    response_model=BatchDetail,
)
async def get_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    batch = await get_batch_details(db, batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found",
        )

    return batch


@router.get(
    "/batches/{batch_id}/documents",
    response_model=list[DocumentListItem],
)
async def get_batch_documents(
    batch_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    documents = await list_batch_documents(
        session=db,
        batch_id=batch_id,
        offset=offset,
        limit=limit,
    )

    if documents is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found",
        )

    return documents


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetail,
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    document = await get_document_details(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


@router.get(
    "/batches/{batch_id}/summary",
    response_model=BatchSummary,
)
async def get_batch_summary_endpoint(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    summary = await get_batch_summary(db, batch_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found",
        )

    return summary
