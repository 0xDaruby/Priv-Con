"""Watermark/page-number contracts, displayed geometry and lifecycle checks."""

import json
import time
from io import BytesIO

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from app.config import settings
from app.main import app
from app.services.job_service import job_manager


def fixture_pdf() -> bytes:
    with pymupdf.open() as doc:
        for i in range(4):
            page = doc.new_page(width=400 + i * 20, height=500 + i * 20)
            page.insert_text((60, 100), f"SOURCE {i + 1}")
        data = doc.tobytes()
    writer = PdfWriter(clone_from=BytesIO(data))
    for i, page in enumerate(writer.pages):
        page.cropbox.lower_left = (20, 30)
        page.cropbox.upper_right = (380 + i * 20, 470 + i * 20)
        page.rotate(i * 90)
    stream = BytesIO()
    writer.write(stream)
    writer.close()
    return stream.getvalue()


def image_bytes() -> bytes:
    stream = BytesIO()
    with Image.new("RGBA", (40, 20), (255, 0, 0, 128)) as image:
        image.save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture()
def overlay_client(tmp_path, monkeypatch):
    uploads, outputs = tmp_path / "uploads", tmp_path / "outputs"
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


def test_image_validation_time_counts_toward_service_deadline(tmp_path, monkeypatch):
    from app.core.exceptions import ConversionError
    from app.services import pdf_watermark_service
    from app.services.pdf_overlay_options import WatermarkOptions

    source, image = tmp_path / "source.pdf", tmp_path / "mark.png"
    source.write_bytes(fixture_pdf())
    image.write_bytes(image_bytes())
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(settings, "output_temp_dir", outputs)
    monkeypatch.setattr(settings, "conversion_timeout_seconds", 60)
    clock = [0.0]
    monkeypatch.setattr(pdf_watermark_service.time, "monotonic", lambda: clock[0])

    def slow_validation(*_):
        clock[0] += 61

    monkeypatch.setattr(
        pdf_watermark_service, "validate_watermark_image", slow_validation
    )
    with pytest.raises(ConversionError) as failure:
        pdf_watermark_service.watermark_pdf(
            source, WatermarkOptions(kind="image", text=None), image
        )
    assert failure.value.code == "conversion_timeout"
    assert not list(outputs.iterdir())


def submit(client, tool="watermark", *, options=None, pages="", pdf=None, image=False):
    files = [("file", ("source.pdf", pdf or fixture_pdf(), "application/pdf"))]
    if image:
        files.append(("watermark_image", ("mark.png", image_bytes(), "image/png")))
    return client.post(
        f"/api/pdf/{tool}",
        files=files,
        data={"pages": pages, "options": json.dumps(options or {})},
    )


def test_watermark_selected_scope_geometry_and_source(overlay_client):
    client, _, _ = overlay_client
    original = fixture_pdf()
    response = submit(
        client, options={"text": "CAFÉ", "angle": 35}, pages="4,1", pdf=original
    )
    assert response.status_code == 200, response.text
    source, result = PdfReader(BytesIO(original)), PdfReader(BytesIO(response.content))
    assert len(result.pages) == 4
    for i, page in enumerate(result.pages):
        assert f"SOURCE {i + 1}" in page.extract_text()
        assert ("CAFÉ" in page.extract_text()) == (i in {0, 3})
        assert page.mediabox == source.pages[i].mediabox
        assert page.cropbox == source.pages[i].cropbox
        assert page.rotation == source.pages[i].rotation


@pytest.mark.parametrize(
    "position",
    [
        "top-left",
        "top-center",
        "top-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ],
)
def test_numbers_displayed_position_all_rotations(overlay_client, position):
    client, _, _ = overlay_client
    response = submit(
        client,
        "page-numbers",
        options={"position": position, "start": 98, "format": "page"},
    )
    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            label = f"Page {98 + i}"
            rects = page.search_for(label)
            assert len(rects) == 1
            rect = rects[0] * page.rotation_matrix
            assert rect.x0 >= 17.9 and rect.x1 <= page.rect.width - 17.9
            assert rect.y0 >= 17.9 and rect.y1 <= page.rect.height - 17.9
            assert (rect.y0 < page.rect.height / 2) == position.startswith("top")
            if position.endswith("left"):
                assert abs(rect.x0 - 18) < 0.2
            elif position.endswith("right"):
                assert abs(rect.x1 - (page.rect.width - 18)) < 0.2
            else:
                assert abs((rect.x0 + rect.x1) / 2 - page.rect.width / 2) < 0.2


def test_numbers_noncontiguous_advance_selected_only(overlay_client):
    client, _, _ = overlay_client
    response = submit(
        client, "page-numbers", options={"start": 9, "format": "page"}, pages="4,2"
    )
    assert response.status_code == 200, response.text
    reader = PdfReader(BytesIO(response.content))
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        assert ("Page 9" in text) == (i == 1)
        assert ("Page 10" in text) == (i == 3)


def test_image_watermark_preserves_transparency(overlay_client):
    client, _, _ = overlay_client
    response = submit(
        client,
        options={"kind": "image", "opacity": 0.5, "scale": 0.5},
        pages="1",
        image=True,
    )
    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        page = doc[0]
        pix = page.get_pixmap()
        center = pix.pixel(pix.width // 2, pix.height // 2)
        assert center[0] > 245 and 175 < center[1] < 210 and 175 < center[2] < 210
        assert not doc[1].get_images()


@pytest.mark.parametrize(
    "tool,options",
    [
        ("watermark", {"text": ""}),
        ("watermark", {"text": "測試"}),
        ("watermark", {"text": "a\nB"}),
        ("watermark", {"text": "x" * 121}),
        ("watermark", {"opacity": 0.09}),
        ("watermark", {"opacity": float("nan")}),
        ("watermark", {"scale": 1.01}),
        ("watermark", {"angle": 181}),
        ("watermark", {"margin": 11}),
        ("watermark", {"font": "C:/private.ttf"}),
        ("watermark", {"kind": "image", "text": "x"}),
        ("watermark", {"angle": True}),
        ("page-numbers", {"start": 1.5}),
        ("page-numbers", {"start": 0}),
        ("page-numbers", {"font_size": 49}),
        ("page-numbers", {"position": "center"}),
        ("page-numbers", {"format": "arbitrary"}),
        ("page-numbers", {"margin": "18"}),
    ],
)
def test_invalid_options_rejected_before_persistence(overlay_client, tool, options):
    client, uploads, outputs = overlay_client
    response = submit(client, tool, options=options)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_overlay_options"
    assert not list(uploads.iterdir()) and not list(outputs.iterdir())


@pytest.mark.parametrize(
    "tool,options,image",
    [
        ("watermark", {"kind": "image"}, False),
        ("watermark", {}, True),
        ("page-numbers", {}, True),
    ],
)
def test_image_consistency_rejected(overlay_client, tool, options, image):
    client, _, _ = overlay_client
    response = submit(client, tool, options=options, image=image)
    assert response.status_code == 400


@pytest.mark.parametrize(
    "route", ["/api/pdf/rotate", "/api/pdf/to-jpg", "/api/jobs/pdf-rotate"]
)
def test_other_tools_reject_watermark_images(overlay_client, route):
    client, _, _ = overlay_client
    response = client.post(
        route,
        files=[
            ("file", ("source.pdf", fixture_pdf())),
            ("watermark_image", ("mark.png", image_bytes())),
        ],
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_overlay_options"


def test_forbidden_image_early_response_closes_spooled_uploads(
    overlay_client, monkeypatch
):
    from starlette.datastructures import UploadFile

    client, _, _ = overlay_client
    closed = []
    original_close = UploadFile.close

    async def close(upload):
        await original_close(upload)
        closed.append(upload.file.closed)

    monkeypatch.setattr(UploadFile, "close", close)
    response = client.post(
        "/api/pdf/rotate",
        files=[
            ("file", ("source.pdf", fixture_pdf())),
            ("watermark_image", ("mark.png", image_bytes())),
        ],
    )
    assert response.status_code == 400
    assert len(closed) == 2 and all(closed)


def test_unsupported_geometry_rejected(overlay_client):
    client, _, _ = overlay_client
    writer = PdfWriter(clone_from=BytesIO(fixture_pdf()))
    writer.pages[0][NameObject("/UserUnit")] = NumberObject(2)
    out = BytesIO()
    writer.write(out)
    writer.close()
    response = submit(client, pdf=out.getvalue())
    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_pdf_geometry"


def test_signed_pdf_rejected(overlay_client):
    client, _, _ = overlay_client
    writer = PdfWriter(clone_from=BytesIO(fixture_pdf()))
    field = DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/V"): DictionaryObject(
                {NameObject("/Type"): NameObject("/Sig")}
            ),
        }
    )
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject(
        {NameObject("/Fields"): ArrayObject([writer._add_object(field)])}
    )
    out = BytesIO()
    writer.write(out)
    writer.close()
    response = submit(client, pdf=out.getvalue())
    assert response.status_code == 400
    assert response.json()["error"] == "signed_pdf_not_supported"


@pytest.mark.parametrize("tool", ["watermark", "page-numbers"])
def test_job_lifecycle_and_download_cleanup(overlay_client, tool):
    client, uploads, outputs = overlay_client
    response = client.post(
        f"/api/jobs/pdf-{tool}",
        files={"file": ("source.pdf", fixture_pdf())},
        data={"options": "{}", "pages": "1,3"},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = client.get(f"/api/jobs/{job_id}").json()
        if state["status"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.01)
    assert state["status"] == "succeeded", state
    assert state["result_content_type"] == "application/pdf"
    assert state["progress_percent"] == 100
    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200 and result.content.startswith(b"%PDF-")
    assert not list(uploads.iterdir()) and not list(outputs.iterdir())


@pytest.mark.parametrize("kind", ["watermark", "page-numbers"])
@pytest.mark.parametrize(
    "stage", ["before", "during", "finalizing", "timeout", "output"]
)
def test_overlay_lifecycle_cleans_owned_output(
    overlay_client, tmp_path, monkeypatch, kind, stage
):
    from app.core.exceptions import PrivConError
    from app.core.progress import JobCancelled
    from app.services.pdf_overlay_options import PageNumberOptions, WatermarkOptions
    from app.services.pdf_page_numbers_service import add_page_numbers
    from app.services.pdf_watermark_service import watermark_pdf

    _, _, outputs = overlay_client
    source = tmp_path / "source.pdf"
    source.write_bytes(fixture_pdf())
    original = source.read_bytes()
    calls = []
    cancelled = stage == "before"

    def cancel():
        if cancelled:
            raise JobCancelled

    def progress(completed, total):
        nonlocal cancelled
        calls.append((completed, total))
        if stage == "during":
            cancelled = True

    def finalizing():
        nonlocal cancelled
        if stage == "finalizing":
            cancelled = True

    if stage == "timeout":
        monkeypatch.setattr(settings, "conversion_timeout_seconds", 0)
    if stage == "output":
        monkeypatch.setattr(settings, "max_output_size_mb", 0)
    service, options = (
        (watermark_pdf, WatermarkOptions())
        if kind == "watermark"
        else (add_page_numbers, PageNumberOptions())
    )
    with pytest.raises((JobCancelled, PrivConError)):
        service(
            source,
            options,
            progress_callback=progress,
            finalizing_callback=finalizing,
            cancellation_check=cancel,
        )
    assert source.read_bytes() == original
    assert not list(outputs.iterdir())
    if stage == "during":
        assert calls == [(1, 4)]


def test_image_resources_reused_across_all_pages(overlay_client):
    client, _, _ = overlay_client
    response = submit(client, options={"kind": "image"}, image=True)
    assert response.status_code == 200, response.text
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        image_refs = [page.get_images()[0][0] for page in doc]
        assert len(set(image_refs)) == 1


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        "null",
        '{"angle":' + "9" * 4000 + "}",
        '{"angle":0,"angle":1}',
        '{"opacity": Infinity}',
        '{"kind":null}',
    ],
)
@pytest.mark.parametrize("route", ["/api/pdf/watermark", "/api/jobs/pdf-watermark"])
def test_malformed_json_options_bounded(overlay_client, route, raw):
    client, _, _ = overlay_client
    response = client.post(
        route, files={"file": ("source.pdf", fixture_pdf())}, data={"options": raw}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_overlay_options"


def test_supported_latin1_spacing_and_hyphen(overlay_client):
    client, _, _ = overlay_client
    response = submit(client, options={"text": "CAFÉ\u00a0Æ\u00adß"})
    assert response.status_code == 200, response.text


def test_image_cap_applies_before_decode(overlay_client, monkeypatch):
    client, _, _ = overlay_client
    monkeypatch.setattr(settings, "max_image_pixels", 10)
    response = submit(client, options={"kind": "image"}, image=True)
    assert response.status_code == 400
    assert response.json()["error"] == "oversized_file"


def test_page_label_must_fit(overlay_client):
    client, _, _ = overlay_client
    response = submit(
        client,
        "page-numbers",
        options={"margin": 144, "font_size": 48, "start": 999999, "format": "page"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_overlay_options"


def test_negative_media_origin_preserved(overlay_client):
    client, _, _ = overlay_client
    writer = PdfWriter(clone_from=BytesIO(fixture_pdf()))
    page = writer.pages[0]
    page.mediabox.lower_left = (-60, -70)
    page.cropbox.lower_left = (-20, -30)
    out = BytesIO()
    writer.write(out)
    writer.close()
    response = submit(client, "page-numbers", pdf=out.getvalue())
    assert response.status_code == 200, response.text
    result = PdfReader(BytesIO(response.content))
    assert list(result.pages[0].mediabox) == [-60, -70, 400, 500]
    assert list(result.pages[0].cropbox) == [-20, -30, 380, 470]


@pytest.mark.parametrize(
    "field,values",
    [
        ("/UserUnit", [0, 2]),
        ("/Rotate", [45]),
        ("/CropBox", [[0, 0, 0, 4], [0, 0, 10000, 300], [5, 4, 3, 2]]),
    ],
)
def test_bad_geometry_rejected_directly(field, values):
    from app.core.exceptions import ValidationError
    from app.services.pdf_overlay_geometry import displayed_geometry

    writer = PdfWriter()
    for value in values:
        page = writer.add_blank_page(width=400, height=500)
        page[NameObject(field)] = (
            ArrayObject([NumberObject(n) for n in value])
            if isinstance(value, list)
            else NumberObject(value)
        )
        with pytest.raises(ValidationError, match="unsupported page geometry"):
            displayed_geometry(page)
    writer.close()


def test_decoded_content_budget_rejected_before_writer_clone(
    overlay_client, tmp_path, monkeypatch
):
    from pypdf.generic import DecodedStreamObject

    from app.core.exceptions import ValidationError
    from app.services import pdf_watermark_service
    from app.services.pdf_overlay_options import WatermarkOptions

    _, _, outputs = overlay_client
    writer = PdfWriter()
    for _ in range(3):
        page = writer.add_blank_page(width=400, height=500)
        stream = DecodedStreamObject()
        stream.set_data(b" " * 500_000)
        page[NameObject("/Contents")] = writer._add_object(stream.flate_encode())
    source = tmp_path / "large-expanded.pdf"
    with source.open("wb") as stream:
        writer.write(stream)
    writer.close()
    monkeypatch.setattr(settings, "max_output_size_mb", 1)

    def cannot_clone(*args, **kwargs):
        raise AssertionError("Must reject before clone")

    monkeypatch.setattr(pdf_watermark_service, "PdfWriter", cannot_clone)
    with pytest.raises(ValidationError, match="safe overlay processing budget"):
        pdf_watermark_service.watermark_pdf(source, WatermarkOptions())
    assert not list(outputs.iterdir())
