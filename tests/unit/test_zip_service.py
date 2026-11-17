
import zipfile

import pytest

from app.services.zip_service import (
    ZipValidationError,
    validate_zip_file,
)


def create_zip(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for filename, content in files:
            archive.writestr(filename, content)


def test_valid_zip_is_accepted(tmp_path):
    zip_path = tmp_path / "valid.zip"

    create_zip(
        zip_path,
        [
            ("contract1.pdf", b"PDF content"),
            ("contract2.docx", b"DOCX content"),
        ],
    )

    documents = validate_zip_file(zip_path)

    assert len(documents) == 2


def test_invalid_zip_is_rejected(tmp_path):
    zip_path = tmp_path / "invalid.zip"
    zip_path.write_bytes(b"This is not a ZIP file")

    with pytest.raises(ZipValidationError):
        validate_zip_file(zip_path)


def test_path_traversal_is_rejected(tmp_path):
    zip_path = tmp_path / "unsafe.zip"

    create_zip(
        zip_path,
        [
            ("../malicious.pdf", b"malicious content"),
        ],
    )

    with pytest.raises(ZipValidationError):
        validate_zip_file(zip_path)


def test_unsupported_extension_is_rejected(tmp_path):
    zip_path = tmp_path / "unsupported.zip"

    create_zip(
        zip_path,
        [
            ("script.exe", b"executable"),
        ],
    )

    with pytest.raises(ZipValidationError):
        validate_zip_file(zip_path)


def test_empty_zip_is_rejected(tmp_path):
    zip_path = tmp_path / "empty.zip"

    with zipfile.ZipFile(zip_path, "w"):
        pass

    with pytest.raises(ZipValidationError):
        validate_zip_file(zip_path)


def test_oversized_document_is_rejected(tmp_path, monkeypatch):
    zip_path = tmp_path / "large.zip"

    create_zip(
        zip_path,
        [
            ("large.pdf", b"A" * 1024),
        ],
    )

    monkeypatch.setattr(
        "app.services.zip_service.settings.MAX_DOCUMENT_SIZE",
        100,
    )

    with pytest.raises(ZipValidationError):
        validate_zip_file(zip_path)
