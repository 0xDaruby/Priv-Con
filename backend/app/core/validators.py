"""Structural validators for Office, PDF, and image uploads."""

import warnings
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import settings
from app.core.exceptions import ValidationError


EXPECTED_EXTENSION = {
    "docx": ".docx",
    "pptx": ".pptx",
    "xlsx": ".xlsx",
}

EXPECTED_INTERNAL_PATH = {
    "docx": "word/document.xml",
    "pptx": "ppt/presentation.xml",
    "xlsx": "xl/workbook.xml",
}

EXPECTED_ROOT_ELEMENT = {
    "docx": "document",
    "pptx": "presentation",
    "xlsx": "workbook",
}

REQUIRED_PACKAGE_PATHS = {
    "[Content_Types].xml": "Types",
    "_rels/.rels": "Relationships",
}

IMAGE_EXTENSION_TO_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def validate_extension(filename: str, tool_key: str) -> None:
    expected = EXPECTED_EXTENSION[tool_key]

    if not (filename or "").lower().endswith(expected):
        raise ValidationError(
            code="unsupported_file_type",
            message=f"Only {expected} files are accepted for this tool.",
        )


def validate_office_structure(file_path: Path, tool_key: str) -> None:
    """Confirm that an Office upload is a coherent ZIP/XML package."""
    if not zipfile.is_zipfile(file_path):
        _raise_invalid_office_document()

    expected_path = EXPECTED_INTERNAL_PATH[tool_key]

    try:
        with zipfile.ZipFile(file_path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]

            if len(names) != len(set(names)):
                _raise_corrupted_office(
                    "This Office document contains duplicate package entries."
                )

            for entry in entries:
                if _is_unsafe_archive_path(entry.filename):
                    _raise_corrupted_office(
                        "This Office document contains an invalid package path."
                    )

                if entry.flag_bits & 0x1:
                    _raise_corrupted_office(
                        "Encrypted Office documents are not supported."
                    )

            required_parts = {
                **REQUIRED_PACKAGE_PATHS,
                expected_path: EXPECTED_ROOT_ELEMENT[tool_key],
            }
            missing_parts = set(required_parts).difference(names)

            if missing_parts:
                _raise_corrupted_office(
                    "This file doesn't match the expected Office document structure."
                )

            for part_name, expected_root in required_parts.items():
                root = _read_office_xml_part(archive, part_name)

                if _local_xml_name(root.tag) != expected_root:
                    _raise_corrupted_office(
                        "This Office document contains an invalid XML structure."
                    )
    except ValidationError:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError) as exc:
        _raise_invalid_office_document(exc)


def validate_office_file(file_path: Path, filename: str, tool_key: str) -> None:
    """Validate an Office upload's extension and package structure."""
    validate_extension(filename, tool_key)
    validate_office_structure(file_path, tool_key)


def validate_pdf_extension(filename: str) -> None:
    """Reject files that are not presented as PDFs before saving them."""
    if not (filename or "").lower().endswith(".pdf"):
        raise ValidationError(
            code="unsupported_file_type",
            message="Only .pdf files are accepted for this tool.",
        )


def validate_pdf_structure(file_path: Path) -> None:
    """Confirm that an uploaded PDF is readable, unencrypted, and non-empty."""
    try:
        with file_path.open("rb") as uploaded_file:
            if b"%PDF-" not in uploaded_file.read(1024):
                raise ValidationError(
                    code="corrupted_file",
                    message="This file isn't a valid or readable PDF.",
                )

        reader = PdfReader(str(file_path), strict=True)

        try:
            if reader.is_encrypted:
                raise ValidationError(
                    code="password_protected",
                    message="Password-protected PDFs are not supported.",
                )

            page_count = len(reader.pages)

            if page_count == 0:
                raise ValidationError(
                    code="empty_pdf",
                    message="PDF files must contain at least one page.",
                )

            for page in reader.pages:
                _ = page.mediabox.width
                _ = page.mediabox.height
        finally:
            reader.close()
    except ValidationError:
        raise
    except (
        OSError,
        PdfReadError,
        EOFError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable PDF.",
        ) from exc


def validate_pdf_file(file_path: Path, filename: str) -> None:
    """Validate a PDF upload's extension and content structure."""
    validate_pdf_extension(filename)
    validate_pdf_structure(file_path)


def validate_image_extension(filename: str) -> str:
    """Validate an image filename and return its normalized extension."""
    extension = Path(filename or "").suffix.lower()

    if extension not in IMAGE_EXTENSION_TO_FORMAT:
        raise ValidationError(
            code="unsupported_file_type",
            message="Only .jpg, .jpeg, .png, and .webp files are accepted.",
        )

    return extension


def validate_image_structure(file_path: Path, filename: str) -> None:
    """Verify that image content is readable and matches its extension."""
    extension = validate_image_extension(filename)
    expected_format = IMAGE_EXTENSION_TO_FORMAT[extension]

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(file_path) as image:
                actual_format = image.format
                image.verify()

            with Image.open(file_path) as image:
                image.seek(0)
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError(
            code="oversized_file",
            message="The image dimensions exceed safe processing limits.",
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable image.",
        ) from exc

    if actual_format != expected_format:
        raise ValidationError(
            code="file_type_mismatch",
            message="The image content does not match its file extension.",
        )


def validate_image_file(file_path: Path, filename: str) -> None:
    """Validate an image upload's extension and content structure."""
    validate_image_extension(filename)
    validate_image_structure(file_path, filename)


def _read_office_xml_part(
    archive: zipfile.ZipFile,
    part_name: str,
) -> ElementTree.Element:
    entry = archive.getinfo(part_name)
    max_uncompressed_size = settings.max_upload_size_mb * 1024 * 1024

    if entry.file_size > max_uncompressed_size:
        raise ValidationError(
            code="oversized_file",
            message="The Office document contains an oversized internal component.",
        )

    try:
        content = archive.read(part_name)
        return ElementTree.fromstring(content)
    except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="The Office document contains damaged or malformed XML.",
        ) from exc


def _is_unsafe_archive_path(filename: str) -> bool:
    path = PurePosixPath(filename.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts


def _local_xml_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _raise_corrupted_office(message: str) -> None:
    raise ValidationError(code="corrupted_file", message=message)


def _raise_invalid_office_document(exc: Exception | None = None) -> None:
    error = ValidationError(
        code="corrupted_file",
        message=(
            "This file isn't a valid Office document. It may be renamed, "
            "corrupted, or truncated."
        ),
    )

    if exc is None:
        raise error

    raise error from exc
