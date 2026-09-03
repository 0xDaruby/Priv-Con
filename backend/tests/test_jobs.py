"""Truthful asynchronous job progress, result, and cancellation tests."""

import time
import zipfile
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app.config import settings
from app.main import app
from app.services import job_service, libreoffice_service
from app.services.job_service import job_manager

OFFICE_PARTS = {
    "docx": ("word/document.xml", b'<w:document xmlns:w="urn:test"/>'),
    "pptx": ("ppt/presentation.xml", b'<p:presentation xmlns:p="urn:test"/>'),
    "xlsx": ("xl/workbook.xml", b'<x:workbook xmlns:x="urn:test"/>'),
}


def _office_bytes(tool_key: str) -> bytes:
    output = BytesIO()
    internal_path, document_xml = OFFICE_PARTS[tool_key]

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", b'<Types xmlns="urn:test"/>')
        archive.writestr("_rels/.rels", b'<Relationships xmlns="urn:test"/>')
        archive.writestr(internal_path, document_xml)

    return output.getvalue()


def _image_bytes(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    image = Image.new("RGB", (40, 50), color)

    try:
        image.save(output, format="PNG")
    finally:
        image.close()

    return output.getvalue()


def _pdf_bytes(*page_widths: float) -> bytes:
    output = BytesIO()
    writer = PdfWriter()

    try:
        for width in page_widths:
            writer.add_blank_page(width=width, height=100)
        writer.write(output)
    finally:
        writer.close()

    return output.getvalue()


def _wait_for_status(
    client: TestClient,
    job_id: str,
    expected_status: str,
    *,
    timeout: float = 3,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        payload = response.json()

        if payload["status"] == expected_status:
            return payload

        time.sleep(0.01)

    raise AssertionError(f"job {job_id} did not reach {expected_status}")


@pytest.fixture()
def job_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)
    monkeypatch.setattr(settings, "cleanup_mode", "immediate")

    with TestClient(app) as client:
        yield client, upload_dir, output_dir

    assert job_manager.wait_for_idle()
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []


def test_office_job_reports_truthful_stage_then_downloads_and_cleans(
    job_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = job_client
    converting = Event()
    release = Event()

    def fake_convert_to_pdf(
        input_path: Path,
        job_id: str,
        *,
        cancellation_check=None,
    ) -> Path:
        converting.set()

        while not release.wait(0.01):
            if cancellation_check is not None:
                cancellation_check()

        output_directory = output_dir / job_id
        output_directory.mkdir()
        output_path = output_directory / f"{input_path.stem}.pdf"
        output_path.write_bytes(b"%PDF-1.4\n%%EOF")
        return output_path

    monkeypatch.setattr(
        libreoffice_service,
        "convert_to_pdf",
        fake_convert_to_pdf,
    )

    response = client.post(
        "/api/jobs/docx-to-pdf",
        files={"file": ("private report.docx", _office_bytes("docx"))},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert converting.wait(1)

    converting_status = _wait_for_status(client, job_id, "running")
    assert converting_status["stage"] == "converting"
    assert converting_status["progress_percent"] is None
    assert converting_status["result_available"] is False

    premature_result = client.get(f"/api/jobs/{job_id}/result")
    assert premature_result.status_code == 409
    assert premature_result.json()["error"] == "job_not_ready"

    release.set()
    succeeded = _wait_for_status(client, job_id, "succeeded")
    assert succeeded["progress_percent"] == 100
    assert succeeded["result_available"] is True
    assert succeeded["result_filename"] == "private_report.pdf"
    assert succeeded["result_content_type"] == "application/pdf"

    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    assert result.content.startswith(b"%PDF-")
    assert result.headers["content-type"] == "application/x-privcon-result"
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []


def test_merge_job_exposes_real_page_percentage(
    job_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, output_dir = job_client
    halfway = Event()
    release = Event()

    def fake_merge_pdfs(
        input_paths,
        *,
        expected_total_pages=None,
        progress_callback=None,
        finalizing_callback=None,
        cancellation_check=None,
    ) -> Path:
        assert expected_total_pages == 4

        for completed in range(1, 5):
            if cancellation_check is not None:
                cancellation_check()
            if progress_callback is not None:
                progress_callback(completed, 4)
            if completed == 2:
                halfway.set()
                assert release.wait(2)

        if finalizing_callback is not None:
            finalizing_callback()

        output_directory = output_dir / "merge-result"
        output_directory.mkdir()
        output_path = output_directory / "merged.pdf"
        output_path.write_bytes(b"%PDF-1.4\n%%EOF")
        return output_path

    monkeypatch.setattr(job_service, "merge_pdfs", fake_merge_pdfs)

    response = client.post(
        "/api/jobs/pdf-merge",
        files=[
            ("files", ("first.pdf", _pdf_bytes(100, 110))),
            ("files", ("second.pdf", _pdf_bytes(120, 130))),
        ],
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert halfway.wait(1)

    progress = client.get(f"/api/jobs/{job_id}").json()
    assert progress["stage"] == "converting"
    assert progress["progress_percent"] == 50
    assert progress["completed_units"] == 2
    assert progress["total_units"] == 4
    assert progress["unit_label"] == "pages"

    release.set()
    _wait_for_status(client, job_id, "succeeded")
    assert client.get(f"/api/jobs/{job_id}/result").status_code == 200


def test_cancelling_running_job_stops_work_and_cleans_inputs(
    job_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = job_client
    converting = Event()

    def cancellable_convert(
        _input_path: Path,
        _job_id: str,
        *,
        cancellation_check=None,
    ) -> Path:
        converting.set()
        deadline = time.monotonic() + 2

        while time.monotonic() < deadline:
            if cancellation_check is not None:
                cancellation_check()
            time.sleep(0.01)

        raise AssertionError("the job was not cancelled")

    monkeypatch.setattr(
        libreoffice_service,
        "convert_to_pdf",
        cancellable_convert,
    )

    response = client.post(
        "/api/jobs/docx-to-pdf",
        files={"file": ("cancel-me.docx", _office_bytes("docx"))},
    )
    job_id = response.json()["job_id"]
    assert converting.wait(1)

    cancel_response = client.delete(f"/api/jobs/{job_id}")
    assert cancel_response.status_code == 200
    cancelled = _wait_for_status(client, job_id, "cancelled")
    assert cancelled["stage"] == "cancelled"
    assert cancelled["result_available"] is False
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []


def test_unknown_job_returns_controlled_error(job_client) -> None:
    client, _, _ = job_client
    response = client.get("/api/jobs/not-a-real-job")
    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "The requested conversion job was not found.",
    }


@pytest.mark.parametrize(
    ("tool", "tool_key", "filename"),
    [
        ("docx-to-pdf", "docx", "document.docx"),
        ("pptx-to-pdf", "pptx", "slides.pptx"),
        ("xlsx-to-pdf", "xlsx", "workbook.xlsx"),
    ],
)
def test_all_office_job_routes_return_downloadable_results(
    job_client,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    tool_key: str,
    filename: str,
) -> None:
    client, _, output_dir = job_client

    def fake_convert_to_pdf(
        input_path: Path,
        job_id: str,
        *,
        cancellation_check=None,
    ) -> Path:
        if cancellation_check is not None:
            cancellation_check()
        output_directory = output_dir / job_id
        output_directory.mkdir()
        output_path = output_directory / f"{input_path.stem}.pdf"
        output_path.write_bytes(b"%PDF-1.4\n%%EOF")
        return output_path

    monkeypatch.setattr(
        libreoffice_service,
        "convert_to_pdf",
        fake_convert_to_pdf,
    )
    response = client.post(
        f"/api/jobs/{tool}",
        files={"file": (filename, _office_bytes(tool_key))},
    )
    assert response.status_code == 202
    status = _wait_for_status(client, response.json()["job_id"], "succeeded")
    assert status["result_content_type"] == "application/pdf"
    result = client.get(f"/api/jobs/{status['job_id']}/result")
    assert result.status_code == 200
    assert result.content.startswith(b"%PDF-")


def test_split_and_images_job_routes_return_expected_results(job_client) -> None:
    client, _, _ = job_client

    split_response = client.post(
        "/api/jobs/pdf-split",
        files={"file": ("three-pages.pdf", _pdf_bytes(100, 110, 120))},
        data={"mode": "every_page"},
    )
    assert split_response.status_code == 202
    split_status = _wait_for_status(
        client,
        split_response.json()["job_id"],
        "succeeded",
    )
    assert split_status["result_content_type"] == "application/zip"
    assert split_status["result_filename"] == "three-pages_split.zip"
    split_result = client.get(f"/api/jobs/{split_status['job_id']}/result")
    assert split_result.status_code == 200

    with zipfile.ZipFile(BytesIO(split_result.content)) as archive:
        assert archive.namelist() == [
            "three-pages_page_001.pdf",
            "three-pages_page_002.pdf",
            "three-pages_page_003.pdf",
        ]

    image_response = client.post(
        "/api/jobs/images-to-pdf",
        files=[
            ("files", ("first.png", _image_bytes((20, 40, 60)))),
            ("files", ("second.png", _image_bytes((60, 40, 20)))),
        ],
    )
    assert image_response.status_code == 202
    image_status = _wait_for_status(
        client,
        image_response.json()["job_id"],
        "succeeded",
    )
    assert image_status["result_content_type"] == "application/pdf"
    assert image_status["result_filename"] == "images.pdf"
    image_result = client.get(f"/api/jobs/{image_status['job_id']}/result")
    assert image_result.status_code == 200
    assert image_result.content.startswith(b"%PDF-")


def test_pdf_to_word_job_returns_downloadable_docx(
    job_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, output_dir = job_client

    received_mode = ""

    def fake_pdf_to_docx(
        input_path: Path,
        job_id: str,
        *,
        mode: str,
        cancellation_check=None,
    ) -> Path:
        nonlocal received_mode
        received_mode = mode
        if cancellation_check is not None:
            cancellation_check()
        output_directory = output_dir / job_id
        output_directory.mkdir()
        output_path = output_directory / f"{input_path.stem}.docx"
        output_path.write_bytes(_office_bytes("docx"))
        return output_path

    monkeypatch.setattr(job_service, "pdf_to_docx", fake_pdf_to_docx)
    response = client.post(
        "/api/jobs/pdf-to-docx",
        files={"file": ("editable report.pdf", _pdf_bytes(100))},
        data={"mode": "preserve_appearance"},
    )

    assert response.status_code == 202
    status = _wait_for_status(client, response.json()["job_id"], "succeeded")
    assert status["result_filename"] == "editable_report.docx"
    assert "wordprocessingml.document" in status["result_content_type"]
    assert received_mode == "preserve_appearance"

    result = client.get(f"/api/jobs/{status['job_id']}/result")
    assert result.status_code == 200
    with zipfile.ZipFile(BytesIO(result.content)) as archive:
        assert "word/document.xml" in archive.namelist()


def test_pdf_to_word_job_rejects_unknown_conversion_mode(job_client) -> None:
    client, upload_dir, output_dir = job_client
    response = client.post(
        "/api/jobs/pdf-to-docx",
        files={"file": ("editable report.pdf", _pdf_bytes(100))},
        data={"mode": "plain_text"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_conversion_mode"
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []
