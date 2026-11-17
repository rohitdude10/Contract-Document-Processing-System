
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrackingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BatchListItem(TrackingBase):
    id: UUID
    original_filename: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    pending_documents: int
    processing_progress: float
    created_at: datetime
    updated_at: datetime


class BatchDetail(BatchListItem):
    requested_variables: list[str]
    upload_size: int


class DocumentListItem(TrackingBase):
    id: UUID
    batch_id: UUID
    original_filename: str
    file_size: int
    mime_type: str | None
    status: str
    attempt_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class FindingTrackingItem(TrackingBase):
    id: UUID
    variable_name: str
    extracted_value: str
    status: str
    reviewer_comment: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class DocumentDetail(DocumentListItem):
    findings: list[FindingTrackingItem]


class BatchSummary(BaseModel):
    batch_id: UUID

    total_documents: int
    queued_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    pending_documents: int

    total_findings: int
    pending_findings: int
    accepted_findings: int
    rejected_findings: int

    processing_progress: float
    review_progress: float
