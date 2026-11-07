"""Rotation and JPEG export contracts, content and lifecycle regressions."""

import time
import zipfile
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from app.config import settings
from app.core.exceptions import PrivConError
from app.core.progress import JobCancelled
from app.main import app
from app.services import pdf_to_image_service
from app.services.job_service import job_manager
from app.services.pdf_to_image_service import pdf_to_jpeg
from app.services.pdf_to_image_worker import RenderFailure, render_pages
from app.services.pdf_tool_options import JpegOptions


def _pdf_bytes() -> bytes:
    with pymupdf.open() as document:
        for index, size in enumerate(((120, 180), (180, 120), (100, 140)), 1):
            page = document.new_page(width=size[0], height=size[1])
            page.insert_text((15, 30), f"Page {index}")
            page.draw_rect(
                pymupdf.Rect(10, 50, 40, 80), color=(1, 0, 0), fill=(1, 0, 0)
            )
        document[1].set_rotation(90)
        return document.tobytes()


def _signed_pdf_bytes() -> bytes:
    writer = PdfWriter(clone_from=BytesIO(_pdf_bytes()))
    signature = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/ByteRange"): ArrayObject(
                [NumberObject(0), NumberObject(1), NumberObject(2), NumberObject(3)]
            ),
        }
    )
    field = DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/V"): writer._add_object(signature),
        }
    )
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(
        DictionaryObject(
            {NameObject("/Fields"): ArrayObject([writer._add_object(field)])}
        )
    )
    output = BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


@pytest.fixture()
def tool_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    uploads = tmp_path / "uploads"
    outputs = tmp_path / "outputs"
    uploads.mkdir()
    outputs.mkdir()
    monkeypatch.setattr(settings, "upload_temp_dir", uploads)
    monkeypatch.setattr(settings, "output_temp_dir", outputs)
    monkeypatch.setattr(settings, "cleanup_mode", "immediate")
    with TestClient(app) as client:
        yield client, uploads, outputs
    assert job_manager.wait_for_idle(timeout=10)
    assert not list(uploads.iterdir())
    assert not list(outputs.iterdir())


def _submit(client: TestClient, route: str, **data: str):
    return client.post(
        route,
        files={"file": ("private test.pdf", _pdf_bytes(), "application/pdf")},
        data=data,
    )


def _wait(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = client.get(f"/api/jobs/{job_id}").json()
        if result["status"] in {"succeeded", "failed", "cancelled"}:
            return result
        time.sleep(0.02)
    raise AssertionError("Job did not finish")


def test_rotate_selected_pages_preserves_existing_rotation_and_content(tool_client):
    client, _, _ = tool_client
    response = _submit(client, "/api/pdf/rotate", angle="90", pages="3,1")
    assert response.status_code == 200
    document = PdfReader(BytesIO(response.content))
    assert [page.rotation for page in document.pages] == [90, 90, 90]
    assert [page.extract_text().strip() for page in document.pages] == [
        "Page 1",
        "Page 2",
        "Page 3",
    ]


def test_four_rotations_restore_rendering(tool_client):
    client, _, _ = tool_client
    data = _pdf_bytes()
    for _ in range(4):
        response = client.post(
            "/api/pdf/rotate", files={"file": ("test.pdf", data)}, data={"angle": "90"}
        )
        assert response.status_code == 200
        data = response.content
    with (
        pymupdf.open(stream=_pdf_bytes(), filetype="pdf") as original,
        pymupdf.open(stream=data, filetype="pdf") as rotated,
    ):
        assert [page.get_pixmap().samples for page in original] == [
            page.get_pixmap().samples for page in rotated
        ]


@pytest.mark.parametrize(
    "options",
    [
        {"angle": "45"},
        {"angle": "90.5"},
        {"pages": "1-2,2"},
        {"pages": "4"},
        {"pages": "0"},
        {"pages": "2-1"},
    ],
)
def test_rotate_rejects_invalid_options_and_cleans(tool_client, options):
    client, uploads, outputs = tool_client
    response = _submit(client, "/api/pdf/rotate", **options)
    assert response.status_code in {400, 422}
    assert not list(uploads.iterdir())
    assert not list(outputs.iterdir())


def test_rotate_rejects_signed_pdf(tool_client):
    client, _, _ = tool_client
    response = client.post(
        "/api/pdf/rotate", files={"file": ("signed.pdf", _signed_pdf_bytes())}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "signed_pdf_not_supported"


def test_jpeg_single_selection_has_correct_dpi_rotation_and_dimensions(tool_client):
    client, _, _ = tool_client
    response = _submit(client, "/api/pdf/to-jpg", pages="2", dpi="144", quality="85")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "JPEG"
        assert image.size == (240, 360)
        assert image.mode == "RGB"
        assert image.getextrema() != ((255, 255), (255, 255), (255, 255))


def test_jpeg_multiple_pages_zip_is_source_order(tool_client):
    client, _, _ = tool_client
    response = _submit(client, "/api/pdf/to-jpg", pages="3,1", dpi="72")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            "private_test_page_001.jpg",
            "private_test_page_003.jpg",
        ]
        for name in archive.namelist():
            with Image.open(BytesIO(archive.read(name))) as image:
                image.verify()


@pytest.mark.parametrize(
    "options",
    [
        {"dpi": "71"},
        {"dpi": "301"},
        {"dpi": "nan"},
        {"quality": "39"},
        {"quality": "96"},
        {"pages": "1,1"},
        {"pages": "5"},
    ],
)
def test_jpeg_rejects_invalid_options(tool_client, options):
    client, _, _ = tool_client
    assert _submit(client, "/api/pdf/to-jpg", **options).status_code in {400, 422}


@pytest.mark.parametrize(
    "tool,options,mime",
    [
        ("pdf-rotate", {"angle": "180", "pages": "1"}, "application/pdf"),
        ("pdf-to-jpg", {"pages": "1", "dpi": "72"}, "image/jpeg"),
        ("pdf-to-jpg", {"pages": "1-2", "dpi": "72"}, "application/zip"),
    ],
)
def test_async_tools_download_once_and_cleanup(tool_client, tool, options, mime):
    client, uploads, outputs = tool_client
    response = _submit(client, f"/api/jobs/{tool}", **options)
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    snapshot = _wait(client, job_id)
    assert snapshot["status"] == "succeeded", snapshot
    assert snapshot["result_content_type"] == mime
    assert not list(uploads.iterdir())
    assert client.get(f"/api/jobs/{job_id}/result").status_code == 200
    assert client.get(f"/api/jobs/{job_id}/result").status_code == 410
    assert not list(outputs.iterdir())


@pytest.mark.parametrize(
    "limit,threshold",
    [("max_pdf_render_pixels", 100), ("max_total_pdf_render_pixels", 30_000)],
)
def test_jpeg_rejects_pixel_budget_before_rendering(
    tool_client, monkeypatch, limit, threshold
):
    client, uploads, outputs = tool_client
    monkeypatch.setattr(settings, limit, threshold)
    response = _submit(client, "/api/pdf/to-jpg", dpi="72")
    assert response.status_code == 422
    assert response.json()["error"] == "render_too_large"
    assert not list(uploads.iterdir())
    assert not list(outputs.iterdir())


def test_jpeg_rejects_output_over_budget(tool_client, monkeypatch):
    client, _, _ = tool_client
    monkeypatch.setattr(settings, "max_output_size_mb", 0)
    response = _submit(client, "/api/pdf/to-jpg", pages="1", dpi="72")
    assert response.status_code == 422
    assert response.json()["error"] == "output_too_large"


@pytest.mark.parametrize("stop", ["timeout", "cancel", "crash"])
def test_jpeg_stops_owned_worker_and_cleans_on_interruption(
    tool_client, tmp_path, monkeypatch, stop
):
    import subprocess
    import sys

    _, _, outputs = tool_client
    source = tmp_path / "source.pdf"
    source.write_bytes(_pdf_bytes())
    original_popen = subprocess.Popen
    processes = []

    def start_worker(command, **kwargs):
        script = "import sys; sys.stdin.read(); " + (
            "sys.exit(3)" if stop == "crash" else "import time; time.sleep(30)"
        )
        process = original_popen([sys.executable, "-c", script], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(pdf_to_image_service.subprocess, "Popen", start_worker)
    if stop == "timeout":
        monkeypatch.setattr(settings, "conversion_timeout_seconds", 0.3)
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        if stop == "cancel" and calls >= 2:
            raise JobCancelled()

    expected = JobCancelled if stop == "cancel" else PrivConError
    with pytest.raises(expected) as raised:
        pdf_to_jpeg(
            source,
            "source.pdf",
            JpegOptions(pages="1", dpi=72),
            cancellation_check=cancelled,
        )
    if stop == "timeout":
        assert raised.value.code == "conversion_timeout"
    assert len(processes) == 1
    assert processes[0].poll() is not None
    assert not list(outputs.iterdir())


@pytest.mark.parametrize("route", ["/api/pdf/rotate", "/api/pdf/to-jpg"])
def test_tools_keep_existing_strict_upload_validation(tool_client, route):
    client, _, _ = tool_client
    assert client.post(route).status_code == 400
    assert (
        client.post(
            route,
            files=[
                ("file", ("a.pdf", _pdf_bytes())),
                ("file", ("b.pdf", _pdf_bytes())),
            ],
        ).status_code
        == 400
    )
    assert (
        client.post(route, files={"file": ("a.pdf", b"not a pdf")}).status_code == 400
    )
    writer = PdfWriter(clone_from=BytesIO(_pdf_bytes()))
    writer.encrypt("secret")
    data = BytesIO()
    writer.write(data)
    writer.close()
    assert (
        client.post(
            route, files={"file": ("encrypted.pdf", data.getvalue())}
        ).status_code
        == 400
    )


@pytest.mark.parametrize("tool", ["pdf-rotate", "pdf-to-jpg"])
def test_async_invalid_pages_fail_and_cleanup(tool_client, tool):
    client, uploads, outputs = tool_client
    response = _submit(client, f"/api/jobs/{tool}", pages="4")
    assert response.status_code == 202
    snapshot = _wait(client, response.json()["job_id"])
    assert snapshot["status"] == "failed"
    assert snapshot["error"]["error"] == "invalid_page_ranges"
    assert not list(uploads.iterdir())
    assert not list(outputs.iterdir())


@pytest.mark.parametrize("indices", [[0], [0, 2]])
def test_renderer_worker_outputs_verified_images(tmp_path, indices):
    source = tmp_path / "source.pdf"
    source.write_bytes(_pdf_bytes())
    output = tmp_path / "rendered"
    output.mkdir()
    result = render_pages(
        {
            "input_path": str(source),
            "output_dir": str(output),
            "indices": indices,
            "dpi": 72,
            "quality": 85,
            "page_count": 3,
            "stem": "test",
            "max_page_pixels": 40_000_000,
            "max_total_pixels": 100_000_000,
            "max_bytes": 1_000_000,
        }
    )
    assert (output / result["name"]).is_file()
    assert result["media_type"] == (
        "image/jpeg" if len(indices) == 1 else "application/zip"
    )


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"page_count": 4}, "conversion_failed"),
        ({"max_page_pixels": 10}, "render_too_large"),
        ({"max_total_pixels": 10}, "render_too_large"),
        ({"max_bytes": 1}, "output_too_large"),
    ],
)
def test_renderer_worker_rejects_invalid_or_oversized_work(tmp_path, overrides, code):
    source = tmp_path / "source.pdf"
    source.write_bytes(_pdf_bytes())
    output = tmp_path / "rendered"
    output.mkdir()
    spec = {
        "input_path": str(source),
        "output_dir": str(output),
        "indices": [0, 1],
        "dpi": 72,
        "quality": 85,
        "page_count": 3,
        "stem": "test",
        "max_page_pixels": 40_000_000,
        "max_total_pixels": 100_000_000,
        "max_bytes": 1_000_000,
        **overrides,
    }
    with pytest.raises(RenderFailure) as raised:
        render_pages(spec)
    assert raised.value.code == code


@pytest.mark.parametrize("route", ["/api/pdf/rotate", "/api/pdf/to-jpg", "/api/jobs/pdf-rotate", "/api/jobs/pdf-to-jpg"])
def test_huge_page_number_is_a_validation_error(tool_client, route):
    client, uploads, outputs = tool_client
    response = _submit(client, route, pages="9" * 5000)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_page_ranges"
    assert not list(uploads.iterdir())
    assert not list(outputs.iterdir())


def test_jpeg_deadline_stops_worker_that_never_reads_input(tool_client, tmp_path, monkeypatch):
    import subprocess
    import sys
    import threading
    import time

    _, _, outputs = tool_client
    source = tmp_path / "source.pdf"
    source.write_bytes(_pdf_bytes())
    original_popen = subprocess.Popen
    processes = []
    errors = []

    def start_worker(command, **kwargs):
        process = original_popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(pdf_to_image_service.subprocess, "Popen", start_worker)
    monkeypatch.setattr(pdf_to_image_service, "validate_pdf_structure", lambda _: 2000)
    monkeypatch.setattr(settings, "conversion_timeout_seconds", 0.3)

    def run():
        try:
            pdf_to_jpeg(source, "source.pdf", JpegOptions(dpi=72))
        except PrivConError as exc:
            errors.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    started = time.monotonic()
    thread.start()
    thread.join(timeout=3)
    stopped_on_deadline = not thread.is_alive()
    # Always stop this synthetic child, even when testing the old blocking bug.
    for process in processes:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
    thread.join(timeout=3)
    assert stopped_on_deadline, "A stalled renderer blocked deadline polling"
    assert time.monotonic() - started < 4
    assert errors and errors[0].code == "conversion_timeout"
    assert not list(outputs.iterdir())
