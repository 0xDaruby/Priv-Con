"""Endpoint tests for Phase 1 step 5: PDF merge."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.main import app
from app.routers import pdf as pdf_router


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


def _empty_pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.write(output)
    writer.close()
    return output.getvalue()


def _assert_temp_dirs_empty(*directories: Path) -> None:
    for directory in directories:
        assert list(directory.iterdir()) == []


@pytest.fixture()
def merge_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()

    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)

    with TestClient(app) as client:
        yield client, upload_dir, output_dir

    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_preserves_file_and_page_order_and_downloads_pdf(merge_client) -> None:
    client, upload_dir, output_dir = merge_client

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("first.pdf", _pdf_bytes(101, 102), "application/pdf")),
            ("files", ("second.pdf", _pdf_bytes(201), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="merged.pdf"' in response.headers["content-disposition"]

    merged_reader = PdfReader(BytesIO(response.content))
    assert [float(page.mediabox.width) for page in merged_reader.pages] == [
        101.0,
        102.0,
        201.0,
    ]
    merged_reader.close()
    _assert_temp_dirs_empty(upload_dir, output_dir)


@pytest.mark.parametrize("file_count", [0, 1])
def test_merge_rejects_fewer_than_two_files(merge_client, file_count: int) -> None:
    client, upload_dir, output_dir = merge_client

    files = []

    if file_count == 1:
        files.append(("files", ("only.pdf", _pdf_bytes(100), "application/pdf")))

    response = client.post(
        "/api/pdf/merge",
        files=files,
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "invalid_input",
        "message": "Upload at least two PDF files to merge.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_rejects_non_pdf_extension(merge_client) -> None:
    client, upload_dir, output_dir = merge_client

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("valid.pdf", _pdf_bytes(100), "application/pdf")),
            ("files", ("renamed.txt", _pdf_bytes(200), "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file_type"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_rejects_corrupt_pdf(merge_client) -> None:
    client, upload_dir, output_dir = merge_client

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("valid.pdf", _pdf_bytes(100), "application/pdf")),
            ("files", ("broken.pdf", b"%PDF-1.4\nnot a pdf", "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "corrupted_file"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_rejects_password_protected_pdf(merge_client) -> None:
    client, upload_dir, output_dir = merge_client

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("valid.pdf", _pdf_bytes(100), "application/pdf")),
            ("files", ("protected.pdf", _encrypted_pdf_bytes(), "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "password_protected",
        "message": "Password-protected PDFs cannot be merged.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_rejects_empty_pdf(merge_client) -> None:
    client, upload_dir, output_dir = merge_client

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("valid.pdf", _pdf_bytes(100), "application/pdf")),
            ("files", ("empty.pdf", _empty_pdf_bytes(), "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "empty_pdf",
        "message": "PDF files must contain at least one page.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_merge_cleans_prior_uploads_when_a_later_save_fails(
    merge_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = merge_client
    real_save_upload = pdf_router.save_upload_to_temp
    call_count = 0

    def fail_second_save(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise OSError("simulated upload failure")

        return real_save_upload(*args, **kwargs)

    monkeypatch.setattr(pdf_router, "save_upload_to_temp", fail_second_save)

    response = client.post(
        "/api/pdf/merge",
        files=[
            ("files", ("first.pdf", _pdf_bytes(100), "application/pdf")),
            ("files", ("second.pdf", _pdf_bytes(200), "application/pdf")),
        ],
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "file_processing_failed",
        "message": "The uploaded files could not be processed.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)
