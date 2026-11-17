
import json
import logging
import shutil
import tempfile

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.schemas.batch import (
    BatchUploadResponse,
    DocumentUploadResponse,
)
from app.services.batch_service import create_batch
from app.services.zip_service import ZipValidationError
from app.workers.publisher import publish_batch_tasks


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/batches",
    tags=["Batches"],
)


@router.post(
    "",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_batch(
    file: UploadFile = File(...),
    requested_variables: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a ZIP archive and create a batch with document records.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    if Path(file.filename).suffix.lower() != ".zip":
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported.",
        )

    # Parse and validate requested extraction variables.
    try:
        payload = json.loads(requested_variables)

        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")

        variables = payload.get("variables")

        if (
            not isinstance(variables, list)
            or not variables
            or len(variables) > 50
        ):
            raise ValueError(
                "Provide between 1 and 50 requested variables."
            )

        if not all(
            isinstance(item, str)
            and item.strip()
            and len(item) <= 100
            for item in variables
        ):
            raise ValueError("Every variable must be a valid string.")

        variables = list(dict.fromkeys(
            item.strip() for item in variables
        ))

    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid requested_variables: {exc}",
        ) from exc

    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    temporary_path = None
    upload_size = 0

    try:
        # Stream the upload to disk and enforce the compressed ZIP limit.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".zip",
            dir=settings.TEMP_DIR,
            delete=False,
        ) as temporary_file:

            temporary_path = Path(temporary_file.name)

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                upload_size += len(chunk)

                if upload_size > settings.MAX_ZIP_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="ZIP upload exceeds the maximum allowed size.",
                    )

                temporary_file.write(chunk)

        if upload_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded ZIP file is empty.",
            )

        batch = await create_batch(
            db=db,
            zip_path=temporary_path,
            original_filename=Path(file.filename).name,
            upload_size=upload_size,
            requested_variables=variables,
        )

        await publish_batch_tasks(
            batch_id=batch.id,
            documents=batch.documents,
        )

        return BatchUploadResponse(
            batch_id=batch.id,
            filename=batch.original_filename,
            status=batch.status,
            total_documents=batch.total_documents,
            documents=[
                DocumentUploadResponse(
                    document_id=document.id,
                    filename=document.original_filename,
                    status=document.status,
                )
                for document in batch.documents
            ],
        )

    except ZipValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to create document batch")

        raise HTTPException(
            status_code=500,
            detail="Unable to process ZIP upload.",
        ) from exc

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)

        await file.close()
