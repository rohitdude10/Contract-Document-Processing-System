
import uuid

from pydantic import BaseModel, Field


class BatchUploadResponse(BaseModel):
    batch_id: uuid.UUID
    filename: str
    status: str
    total_documents: int
    documents: list["DocumentUploadResponse"]


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str


BatchUploadResponse.model_rebuild()
