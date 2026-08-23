"""
Minimal structural validation for Office documents, run BEFORE any file
reaches libreoffice_service.convert_to_pdf().

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
