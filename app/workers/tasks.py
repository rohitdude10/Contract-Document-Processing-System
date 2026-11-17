
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models import (
    Batch,
    Document,
    Finding,
    ProcessingAttempt,
)
from app.services.extraction import (
    MockExtractionProvider,
)

logger = logging.getLogger(__name__)

extraction_provider = MockExtractionProvider()


def utc_now():
    return datetime.now(timezone.utc)


async def process_document(
    batch_id: UUID,
    document_id: UUID,
) -> None:
    """
    Process one document.

    The first transaction claims the document.
    Extraction happens outside the transaction.
    The second transaction persists findings and final status.
    """

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Document)
                .where(
                    Document.id == document_id,
                    Document.batch_id == batch_id,
                )
                .with_for_update()
            )

            document = result.scalar_one_or_none()

            if document is None:
                raise ValueError(
                    f"Document {document_id} does not exist"
                )

            if document.status == "completed":
                logger.info(
                    "Skipping already completed document %s",
                    document_id,
                )
                return

            # A duplicate delivery should not start a second
            # extraction while another worker is processing it.
            if document.status == "processing":
                logger.info(
                    "Document %s is already processing",
                    document_id,
                )
                return

            batch = await session.get(Batch, batch_id)

            if batch is None:
                raise ValueError(f"Batch {batch_id} does not exist")

            document.status = "processing"
            document.attempt_count += 1

            attempt = ProcessingAttempt(
                document_id=document_id,
                attempt_number=document.attempt_count,
                status="processing",
                started_at=utc_now(),
            )

            session.add(attempt)
            await session.flush()
            attempt_id = attempt.id

            document_path = Path(document.stored_path)
            requested_variables = list(batch.requested_variables)
            

    # Do not hold a database transaction open during extraction.
    try:
        findings = await extraction_provider.extract(
            document_path=document_path,
            requested_variables=requested_variables,
        )

    except Exception as exc:
        logger.exception(
            "Extraction failed for document %s",
            document_id,
        )

        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(Document)
                    .where(Document.id == document_id)
                    .with_for_update()
                )
                document = result.scalar_one()

                attempt = await session.get(
                    ProcessingAttempt,
                    attempt_id,
                )

                if attempt:
                    attempt.status = "failed"
                    attempt.finished_at = utc_now()
                    attempt.error_type = type(exc).__name__
                    attempt.error_message = str(exc)[:2000]

                document.error_message = str(exc)[:2000]
                document.status = "queued"

        raise

    # Persist all findings and status changes atomically.
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Document)
                .where(Document.id == document_id)
                .with_for_update()
            )
            document = result.scalar_one()

            if document.status == "completed":
                return

            attempt = await session.get(
                ProcessingAttempt,
                attempt_id,
            )

            for item in findings:
                session.add(
                    Finding(
                        document_id=document_id,
                        variable_name=item.variable_name,
                        extracted_value=item.extracted_value,
                        status="pending",
                    )
                )

            document.status = "completed"
            document.error_message = None

            if attempt:
                attempt.status = "completed"
                attempt.finished_at = utc_now()

            # Recalculate batch progress using database state.
            batch = await session.get(Batch, batch_id)

            completed_count = await session.scalar(
                select(func.count(Document.id)).where(
                    Document.batch_id == batch_id,
                    Document.status == "completed",
                )
            )

            failed_count = await session.scalar(
                select(func.count(Document.id)).where(
                    Document.batch_id == batch_id,
                    Document.status == "failed",
                )
            )

            batch.processed_documents = completed_count or 0
            batch.failed_documents = failed_count or 0

            total = batch.total_documents
            finished = batch.processed_documents + batch.failed_documents

            if finished < total:
                batch.status = "processing"
            elif batch.failed_documents == total:
                batch.status = "failed"
            elif batch.failed_documents > 0:
                batch.status = "partially_completed"
            else:
                batch.status = "completed"

    logger.info(
        "Document processed successfully: %s",
        document_id,
    )
