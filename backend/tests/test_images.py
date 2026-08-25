"""Endpoint tests for Phase 1 step 7: images to PDF."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

from app.config import settings
from app.main import app
from app.services.image_service import load_image_for_pdf


def _image_bytes(
    image_format: str,
    size: tuple[int, int] = (20, 30),
    color: tuple[int, ...] = (20, 40, 60),
    mode: str = "RGB",
    exif: Image.Exif | None = None,
) -> bytes:
    output = BytesIO()
    image = Image.new(mode, size, color)

    try:
        save_options = {"format": image_format}

        if exif is not None:
            save_options["exif"] = exif

        image.save(output, **save_options)
    finally:
        image.close()

    return output.getvalue()


def _pdf_page_sizes(pdf_content: bytes) -> list[tuple[float, float]]:
    reader = PdfReader(BytesIO(pdf_content))

    try:
        return [
            (float(page.mediabox.width), float(page.mediabox.height))
            for page in reader.pages
        ]
    finally:
        reader.close()


def _assert_temp_dirs_empty(*directories: Path) -> None:
    for directory in directories:
        assert list(directory.iterdir()) == []


@pytest.fixture()
def image_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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


@pytest.mark.parametrize(
    ("extension", "image_format"),
    [
        ("jpg", "JPEG"),
        ("jpeg", "JPEG"),
        ("png", "PNG"),
        ("webp", "WEBP"),
    ],
)
def test_images_to_pdf_supports_mvp_formats(
    image_client,
    extension: str,
    image_format: str,
) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post(
        "/api/images/to-pdf",
        files=[
            (
                "files",
                (
                    f"image.{extension}",
                    _image_bytes(image_format),
                    f"image/{extension}",
                ),
            )
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="images.pdf"' in response.headers["content-disposition"]
    assert _pdf_page_sizes(response.content) == [(20.0, 30.0)]
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_preserves_order_and_source_dimensions(image_client) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post(
        "/api/images/to-pdf",
        files=[
            (
                "files",
                ("wide.png", _image_bytes("PNG", (40, 20)), "image/png"),
            ),
            (
                "files",
                ("tall.png", _image_bytes("PNG", (15, 35)), "image/png"),
            ),
        ],
    )

    assert response.status_code == 200
    assert _pdf_page_sizes(response.content) == [
        (40.0, 20.0),
        (15.0, 35.0),
    ]
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_applies_exif_orientation(image_client) -> None:
    client, upload_dir, output_dir = image_client
    exif = Image.Exif()
    exif[274] = 6

    response = client.post(
        "/api/images/to-pdf",
        files=[
            (
                "files",
                (
                    "rotated.jpg",
                    _image_bytes("JPEG", (10, 20), exif=exif),
                    "image/jpeg",
                ),
            )
        ],
    )

    assert response.status_code == 200
    assert _pdf_page_sizes(response.content) == [(20.0, 10.0)]
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_load_image_for_pdf_flattens_transparency_onto_white(tmp_path: Path) -> None:
    image_path = tmp_path / "transparent.png"
    source_image = Image.new("RGBA", (2, 1))
    source_image.putpixel((0, 0), (255, 0, 0, 0))
    source_image.putpixel((1, 0), (0, 0, 255, 255))
    source_image.save(image_path, format="PNG")
    source_image.close()

    prepared_image = load_image_for_pdf(image_path)

    try:
        assert prepared_image.mode == "RGB"
        assert prepared_image.getpixel((0, 0)) == (255, 255, 255)
        assert prepared_image.getpixel((1, 0)) == (0, 0, 255)
    finally:
        prepared_image.close()


def test_images_to_pdf_rejects_missing_files(image_client) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post("/api/images/to-pdf")

    assert response.status_code == 400
    assert response.json() == {
        "error": "invalid_input",
        "message": "Upload at least one image to convert.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_unsupported_extension_and_cleans_prior_uploads(
    image_client,
) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post(
        "/api/images/to-pdf",
        files=[
            ("files", ("valid.png", _image_bytes("PNG"), "image/png")),
            ("files", ("bitmap.bmp", _image_bytes("BMP"), "image/bmp")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file_type"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_corrupt_image(image_client) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post(
        "/api/images/to-pdf",
        files=[("files", ("broken.png", b"not an image", "image/png"))],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "corrupted_file"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_mismatched_content(image_client) -> None:
    client, upload_dir, output_dir = image_client

    response = client.post(
        "/api/images/to-pdf",
        files=[("files", ("renamed.jpg", _image_bytes("PNG"), "image/jpeg"))],
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "file_type_mismatch",
        "message": "The image content does not match its file extension.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_oversized_upload_while_streaming(
    image_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = image_client
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)

    response = client.post(
        "/api/images/to-pdf",
        files=[
            (
                "files",
                ("large.png", b"x" * (1024 * 1024 + 1), "image/png"),
            )
        ],
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "oversized_file",
        "message": "Files larger than 1 MB are not accepted.",
    }
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_excessive_decoded_pixels(
    image_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = image_client
    monkeypatch.setattr(settings, "max_image_pixels", 100)

    response = client.post(
        "/api/images/to-pdf",
        files=[("files", ("large.png", _image_bytes("PNG"), "image/png"))],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "oversized_file"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_images_to_pdf_rejects_excessive_combined_pixels(
    image_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = image_client
    monkeypatch.setattr(settings, "max_total_image_pixels", 700)

    response = client.post(
        "/api/images/to-pdf",
        files=[
            ("files", ("one.png", _image_bytes("PNG", (20, 20)), "image/png")),
            ("files", ("two.png", _image_bytes("PNG", (20, 20)), "image/png")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "oversized_file"
    _assert_temp_dirs_empty(upload_dir, output_dir)
