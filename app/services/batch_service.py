
import shutil
import uuid

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.batch import Batch
from app.models.document import Document
from app.services.zip_service import (
    extract_documents,
    validate_zip_file,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def create_batch(
    db: AsyncSession,
    zip_path: Path,
    original_filename: str,
    upload_size: int,
    requested_variables: list[str],
) -> Batch:
    """
    Extract documents and persist batch/document records.

    If extraction or database persistence fails, clean up
    the files created for this batch.
    """

    batch_id = uuid.uuid4()

    batch_directory = settings.UPLOAD_DIR / str(batch_id)

    try:
        validated_entries = validate_zip_file(zip_path)

        extracted_documents = extract_documents(
            zip_path=zip_path,
            batch_directory=batch_directory,
            validated_entries=validated_entries,
        )

        batch = Batch(
            id=batch_id,
            original_filename=original_filename,
            requested_variables=requested_variables,
            upload_size=upload_size,
            status="queued",
            total_documents=len(extracted_documents),
            processed_documents=0,
            failed_documents=0,
        )

        for extracted in extracted_documents:
            document = Document(
                id=extracted["id"],
                batch_id=batch_id,
                original_filename=extracted["original_filename"],
                stored_path=extracted["stored_path"],
                file_size=extracted["file_size"],
                mime_type=extracted["mime_type"],
                status="queued",
                attempt_count=0,
            )

            batch.documents.append(document)

        db.add(batch)
        await db.commit()

        # Explicitly load the batch and its documents.
        result = await db.execute(
            select(Batch)
            .options(selectinload(Batch.documents))
            .where(Batch.id == batch_id)
        )

        batch = result.scalar_one()

        return batch

    except Exception:
        await db.rollback()
        shutil.rmtree(batch_directory, ignore_errors=True)
        raise
