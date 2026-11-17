
import os
import shutil
import stat
import uuid
import zipfile

from pathlib import Path, PurePosixPath, PureWindowsPath

from app.config import settings


class ZipValidationError(Exception):
    """Raised when an uploaded ZIP is invalid or unsafe."""


def validate_zip_file(zip_path: Path) -> list[zipfile.ZipInfo]:
    """
    Validate ZIP contents without extracting files.

    Returns the list of valid document entries.
    """

    if not zipfile.is_zipfile(zip_path):
        raise ZipValidationError("Uploaded file is not a valid ZIP archive.")

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            entries = archive.infolist()

            documents = []
            total_uncompressed_size = 0
            seen_paths = set()

            for entry in entries:
                if entry.is_dir():
                    continue

                if entry.flag_bits & 0x1:
                    raise ZipValidationError(
                        "Encrypted ZIP entries are not supported."
                    )

                # Reject symbolic links.
                unix_mode = (entry.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    raise ZipValidationError(
                        "Symbolic links are not allowed in ZIP archives."
                    )

                # Normalize and validate archive paths.
                raw_name = entry.filename

                if "\x00" in raw_name:
                    raise ZipValidationError(
                        "Invalid filename in ZIP archive."
                    )

                posix_path = PurePosixPath(raw_name)
                windows_path = PureWindowsPath(raw_name)

                if (
                    posix_path.is_absolute()
                    or windows_path.is_absolute()
                    or windows_path.drive
                    or ".." in posix_path.parts
                    or ".." in windows_path.parts
                ):
                    raise ZipValidationError(
                        "ZIP contains an unsafe file path."
                    )

                normalized_name = raw_name.replace("\\", "/").casefold()

                if normalized_name in seen_paths:
                    raise ZipValidationError(
                        "ZIP contains duplicate file paths."
                    )

                seen_paths.add(normalized_name)

                # Reject unsupported file extensions.
                extension = Path(raw_name).suffix.lower()

                if extension not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
                    raise ZipValidationError(
                        f"Unsupported file format: {extension or 'unknown'}"
                    )

                if entry.file_size > settings.MAX_DOCUMENT_SIZE:
                    raise ZipValidationError(
                        f"Document exceeds maximum size of "
                        f"{settings.MAX_DOCUMENT_SIZE // (1024 * 1024)} MB: "
                        f"{raw_name}"
                    )

                if entry.file_size < 0:
                    raise ZipValidationError("Invalid document size.")

                if entry.file_size > 0:
                    if entry.compress_size == 0:
                        raise ZipValidationError(
                            "Invalid compression information."
                        )

                    ratio = entry.file_size / entry.compress_size

                    if ratio > settings.MAX_COMPRESSION_RATIO:
                        raise ZipValidationError(
                            "ZIP contains a suspicious compression ratio."
                        )

                total_uncompressed_size += entry.file_size

                if (
                    total_uncompressed_size
                    > settings.MAX_TOTAL_EXTRACTED_SIZE
                ):
                    raise ZipValidationError(
                        "Total extracted size exceeds the configured limit."
                    )

                documents.append(entry)

            if not documents:
                raise ZipValidationError(
                    "ZIP archive does not contain supported documents."
                )

            if len(documents) > settings.MAX_DOCUMENTS:
                raise ZipValidationError(
                    f"ZIP contains more than {settings.MAX_DOCUMENTS} documents."
                )

            return documents

    except zipfile.BadZipFile as exc:
        raise ZipValidationError("ZIP archive is corrupted.") from exc


def extract_documents(
    zip_path: Path,
    batch_directory: Path,
    validated_entries: list[zipfile.ZipInfo],
) -> list[dict]:
    """
    Extract validated files using generated UUID filenames.

    Original filenames are retained as metadata.
    """

    extracted_documents = []
    batch_directory.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:

            for entry in validated_entries:
                document_id = uuid.uuid4()

                extension = Path(entry.filename).suffix.lower()
                stored_filename = f"{document_id}{extension}"

                destination = batch_directory / stored_filename

                actual_size = 0

                with archive.open(entry, "r") as source:
                    with destination.open("xb") as target:

                        while True:
                            chunk = source.read(1024 * 1024)

                            if not chunk:
                                break

                            actual_size += len(chunk)

                            if actual_size > settings.MAX_DOCUMENT_SIZE:
                                raise ZipValidationError(
                                    "Extracted document exceeds maximum size."
                                )

                            target.write(chunk)

                # Verify the actual extracted size.
                if actual_size != entry.file_size:
                    raise ZipValidationError(
                        f"Extracted size mismatch: {entry.filename}"
                    )

                extracted_documents.append(
                    {
                        "id": document_id,
                        "original_filename": Path(
                            entry.filename.replace("\\", "/")
                        ).name,
                        "stored_path": str(destination),
                        "file_size": actual_size,
                        "mime_type": None,
                    }
                )

        return extracted_documents

    except Exception:
        shutil.rmtree(batch_directory, ignore_errors=True)
        raise
