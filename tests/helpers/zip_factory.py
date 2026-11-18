
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED


def create_zip(files: dict[str, bytes]) -> bytes:
    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)

    return buffer.getvalue()
