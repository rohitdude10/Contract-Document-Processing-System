
from pathlib import Path

import pytest

from app.services.zip_service import (
    ZipValidationError,
    validate_zip_file,
)
from tests.helpers.zip_factory import create_zip


def write_archive(tmp_path: Path, files: dict[str, bytes]) -> Path:
    archive_path = tmp_path / "test.zip"
    archive_path.write_bytes(create_zip(files))
    return archive_path


def test_rejects_invalid_zip(tmp_path):
    archive_path = tmp_path / "invalid.zip"
    archive_path.write_bytes(b"not a zip file")

    with pytest.raises(ZipValidationError):
        validate_zip_file(archive_path)


def test_rejects_unsupported_extension(tmp_path):
    archive_path = write_archive(
        tmp_path,
        {"contract.exe": b"malicious content"},
    )

    with pytest.raises(ZipValidationError):
        validate_zip_file(archive_path)


def test_rejects_path_traversal(tmp_path):
    archive_path = write_archive(
        tmp_path,
        {"../../outside.txt": b"should not escape"},
    )

    with pytest.raises(ZipValidationError):
        validate_zip_file(archive_path)


def test_rejects_empty_zip(tmp_path):
    archive_path = write_archive(tmp_path, {})

    with pytest.raises(ZipValidationError):
        validate_zip_file(archive_path)


def test_accepts_valid_zip(tmp_path):
    archive_path = write_archive(
        tmp_path,
        {
            "contract-1.txt": b"Contract one",
            "contract-2.txt": b"Contract two",
        },
    )

    result = validate_zip_file(archive_path)

    assert len(result) == 2
