"""Endpoint tests for Phase 1 step 6: PDF split."""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.main import app


def _pdf_bytes(*page_widths: float) -> bytes:
    output = BytesIO()
    writer = PdfWriter()

    for width in page_widths:
        writer.add_blank_page(width=width, height=100)

    writer.write(output)
    writer.close()
    return output.getvalue()


def _encrypted_pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    writer.write(output)
    writer.close()
    return output.getvalue()


def _page_widths(pdf_content: bytes) -> list[float]:
    reader = PdfReader(BytesIO(pdf_content))

    try:
        return [float(page.mediabox.width) for page in reader.pages]
    finally:
        reader.close()


def _assert_temp_dirs_empty(*directories: Path) -> None:
    for directory in directories:
        assert list(directory.iterdir()) == []


@pytest.fixture()
def split_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()

    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)
    monkeypatch.setattr(settings, "cleanup_mode", "immediate")

    with TestClient(app) as client:
        yield client, upload_dir, output_dir

    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_every_page_returns_named_zip_entries(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
        files={
            "file": (
                "report.pdf",
                _pdf_bytes(101, 102, 103),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert 'filename="report_split.zip"' in response.headers["content-disposition"]

    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            "report_page_001.pdf",
            "report_page_002.pdf",
            "report_page_003.pdf",
        ]
        assert _page_widths(archive.read("report_page_001.pdf")) == [101.0]
        assert _page_widths(archive.read("report_page_002.pdf")) == [102.0]
        assert _page_widths(archive.read("report_page_003.pdf")) == [103.0]

    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_one_range_returns_pdf(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "ranges", "ranges": "2-3"},
        files={
            "file": (
                "source.pdf",
                _pdf_bytes(101, 102, 103, 104),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert (
        'filename="source_pages_2-3.pdf"'
        in response.headers["content-disposition"]
    )
    assert _page_widths(response.content) == [102.0, 103.0]
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_multiple_ranges_returns_ordered_zip(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "ranges", "ranges": "4,1-2"},
        files={
            "file": (
                "source.pdf",
                _pdf_bytes(101, 102, 103, 104),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            "source_pages_4-4.pdf",
            "source_pages_1-2.pdf",
        ]
        assert _page_widths(archive.read("source_pages_4-4.pdf")) == [104.0]
        assert _page_widths(archive.read("source_pages_1-2.pdf")) == [101.0, 102.0]

    _assert_temp_dirs_empty(upload_dir, output_dir)


@pytest.mark.parametrize(
    ("mode", "ranges"),
    [
        ("ranges", ""),
        ("ranges", "1--3"),
        ("ranges", "1-2,1-2"),
        ("ranges", "1-3,3-4"),
        ("ranges", "4-2"),
        ("ranges", "0-1"),
        ("ranges", "-1-2"),
        ("ranges", "1-6"),
        ("ranges", "1,"),
        ("every_page", "1-2"),
    ],
)
def test_split_rejects_invalid_ranges(split_client, mode: str, ranges: str) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": mode, "ranges": ranges},
        files={
            "file": (
                "source.pdf",
                _pdf_bytes(101, 102, 103, 104, 105),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_page_ranges"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_invalid_mode_before_saving(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "selected_pages"},
        files={
            "file": ("source.pdf", _pdf_bytes(100), "application/pdf")
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_split_mode"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_missing_file(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "invalid_input",
        "message": "Upload exactly one PDF file to split.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_multiple_files(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
        files=[
            ("file", ("first.pdf", _pdf_bytes(100), "application/pdf")),
            ("file", ("second.pdf", _pdf_bytes(200), "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "invalid_input",
        "message": "Upload exactly one PDF file to split.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_non_pdf_extension(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
        files={"file": ("source.txt", _pdf_bytes(100), "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file_type"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_corrupt_pdf(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
        files={"file": ("broken.pdf", b"%PDF-1.4\ninvalid", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "corrupted_file"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_split_rejects_password_protected_pdf(split_client) -> None:
    client, upload_dir, output_dir = split_client

    response = client.post(
        "/api/pdf/split",
        data={"mode": "every_page"},
        files={
            "file": (
                "protected.pdf",
                _encrypted_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "password_protected"
    _assert_temp_dirs_empty(upload_dir, output_dir)
