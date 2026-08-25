"""Tests for upload-size and structural validation hardening."""

import warnings
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.config import Settings
from app.core.exceptions import ValidationError
from app.core.file_utils import save_upload_to_temp
from app.core.validators import validate_office_structure


OFFICE_PARTS = {
    "docx": (
        "word/document.xml",
        b'<w:document xmlns:w="urn:test"/>',
    ),
    "pptx": (
        "ppt/presentation.xml",
        b'<p:presentation xmlns:p="urn:test"/>',
    ),
    "xlsx": (
        "xl/workbook.xml",
        b'<x:workbook xmlns:x="urn:test"/>',
    ),
}


def _office_bytes(
    tool_key: str,
    *,
    overrides: dict[str, bytes] | None = None,
    extra_parts: dict[str, bytes] | None = None,
    omitted_parts: set[str] | None = None,
) -> bytes:
    internal_path, document_xml = OFFICE_PARTS[tool_key]
    parts = {
        "[Content_Types].xml": b'<Types xmlns="urn:test"/>',
        "_rels/.rels": b'<Relationships xmlns="urn:test"/>',
        internal_path: document_xml,
    }
    parts.update(overrides or {})
    parts.update(extra_parts or {})

    for omitted_part in omitted_parts or set():
        parts.pop(omitted_part, None)

    output = BytesIO()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)

    return output.getvalue()


@pytest.mark.parametrize("tool_key", ["docx", "pptx", "xlsx"])
def test_office_validation_accepts_well_formed_packages(
    tmp_path: Path,
    tool_key: str,
) -> None:
    path = tmp_path / f"document.{tool_key}"
    path.write_bytes(_office_bytes(tool_key))

    validate_office_structure(path, tool_key)


def test_office_validation_rejects_missing_package_part(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    path.write_bytes(
        _office_bytes(
            "docx",
            omitted_parts={"_rels/.rels"},
        )
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_office_structure(path, "docx")

    assert exc_info.value.code == "corrupted_file"


def test_office_validation_rejects_wrong_document_root(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    path.write_bytes(
        _office_bytes(
            "docx",
            overrides={"word/document.xml": b"<workbook/>"},
        )
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_office_structure(path, "docx")

    assert exc_info.value.code == "corrupted_file"


def test_office_validation_rejects_unsafe_archive_paths(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    path.write_bytes(
        _office_bytes(
            "docx",
            extra_parts={"../outside.xml": b"<outside/>"},
        )
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_office_structure(path, "docx")

    assert exc_info.value.code == "corrupted_file"


def test_office_validation_rejects_duplicate_entries(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    output = BytesIO()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)

        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", b"<Types/>")
            archive.writestr("[Content_Types].xml", b"<Types/>")
            archive.writestr("_rels/.rels", b"<Relationships/>")
            archive.writestr("word/document.xml", b"<document/>")

    path.write_bytes(output.getvalue())

    with pytest.raises(ValidationError) as exc_info:
        validate_office_structure(path, "docx")

    assert exc_info.value.code == "corrupted_file"


def test_office_validation_rejects_damaged_required_part(tmp_path: Path) -> None:
    path = tmp_path / "document.docx"
    document_xml = OFFICE_PARTS["docx"][1]
    damaged_archive = bytearray(_office_bytes("docx"))
    content_offset = damaged_archive.find(document_xml)
    assert content_offset >= 0
    damaged_archive[content_offset] ^= 0x01
    path.write_bytes(damaged_archive)

    with pytest.raises(ValidationError) as exc_info:
        validate_office_structure(path, "docx")

    assert exc_info.value.code == "corrupted_file"


def test_streaming_upload_limit_removes_partial_file(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    with pytest.raises(ValidationError) as exc_info:
        save_upload_to_temp(
            source=BytesIO(b"four"),
            upload_dir=upload_dir,
            job_id="job",
            original_filename="document.pdf",
            max_size_bytes=3,
        )

    assert exc_info.value.code == "oversized_file"
    assert list(upload_dir.iterdir()) == []


def test_streaming_upload_accepts_exact_limit(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    saved_path = save_upload_to_temp(
        source=BytesIO(b"four"),
        upload_dir=upload_dir,
        job_id="job",
        original_filename="document.pdf",
        max_size_bytes=4,
    )

    assert saved_path.read_bytes() == b"four"


@pytest.mark.parametrize(
    "invalid_setting",
    [
        {"max_upload_size_mb": 0},
        {"conversion_timeout_seconds": 0},
        {"cleanup_delay_minutes": 0},
        {"cleanup_mode": "unknown"},
    ],
)
def test_settings_reject_invalid_safety_configuration(invalid_setting) -> None:
    with pytest.raises(PydanticValidationError):
        Settings(**invalid_setting)
