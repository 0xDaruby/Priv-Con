"""Structural validators for Office, PDF, and image uploads.

All validators run before a file reaches its conversion service. Office
validation remains intentionally minimal until Phase 1 step 9; PDF and image
validation covers the structural checks required by their current endpoints.

Why this exists (see libreoffice-service-notes.md): sandbox testing found
that LibreOffice's headless converter will "successfully" render garbage
input — a plain-text file or random binary renamed to .docx — as a PDF
rather than reject it, returning exit code 0 both times. Exit code / "a PDF
was produced" is therefore not sufficient proof the input was a valid
Office file, so that check has to happen here, first.

Scope (intentionally minimal — this is Phase 1 step 4; full hardening is
step 9):
  1. extension matches what the tool expects
  2. file is a valid ZIP container
  3. the ZIP contains the internal path expected for its claimed type

Deliberately NOT in scope here (deferred to step 9): file size limits,
deeper XML well-formedness checks, malware scanning, or detecting a
truncated-but-technically-valid zip.
"""

import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import ValidationError

# tool key -> accepted file extension
EXPECTED_EXTENSION = {
    "docx": ".docx",
    "pptx": ".pptx",
    "xlsx": ".xlsx",
}

# tool key -> a path that must exist inside the zip container for a
# genuine Office file of that type
EXPECTED_INTERNAL_PATH = {
    "docx": "word/document.xml",
    "pptx": "ppt/presentation.xml",
    "xlsx": "xl/workbook.xml",
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
    """Confirm the file is a real ZIP-based Office document of the claimed
    type. Raises ValidationError with a clean, user-facing message on any
    mismatch — this is the check that catches mislabeled/corrupt files
    that LibreOffice itself would silently "succeed" on."""
    if not zipfile.is_zipfile(file_path):
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid Office document. It may be "
            "renamed, corrupted, or truncated.",
        )

    expected_path = EXPECTED_INTERNAL_PATH[tool_key]

    try:
        with zipfile.ZipFile(file_path) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid Office document. It may be "
            "renamed, corrupted, or truncated.",
        )

    if expected_path not in names:
        raise ValidationError(
            code="corrupted_file",
            message="This file doesn't match the expected document "
            "structure for this tool. It may be mislabeled or corrupted.",
        )


def validate_office_file(file_path: Path, filename: str, tool_key: str) -> None:
    """Convenience wrapper: extension check, then structural check."""
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
            if uploaded_file.read(5) != b"%PDF-":
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

            if len(reader.pages) == 0:
                raise ValidationError(
                    code="empty_pdf",
                    message="PDF files must contain at least one page.",
                )
        finally:
            reader.close()
    except ValidationError:
        raise
    except (OSError, PdfReadError, EOFError, ValueError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable PDF.",
        ) from exc


def validate_pdf_file(file_path: Path, filename: str) -> None:
    """Convenience wrapper: PDF extension check, then content validation."""
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
        with Image.open(file_path) as image:
            actual_format = image.format
            image.verify()
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
    """Convenience wrapper for image extension and content validation."""
    validate_image_extension(filename)
    validate_image_structure(file_path, filename)
