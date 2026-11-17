
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    variable_name: str
    extracted_value: str
    status: str
    reviewer_comment: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ReviewRequest(BaseModel):
    status: Literal["accepted", "rejected"]

    reviewer_comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    reviewed_by: str = Field(
        min_length=1,
        max_length=255,
    )


class ReviewStatistics(BaseModel):
    batch_id: UUID
    total_findings: int
    pending_findings: int
    accepted_findings: int
    rejected_findings: int
    reviewed_findings: int
    review_progress: float


class DocumentReviewStatistics(BaseModel):
    document_id: UUID
    total_findings: int
    pending_findings: int
    accepted_findings: int
    rejected_findings: int
    reviewed_findings: int
    review_progress: float
