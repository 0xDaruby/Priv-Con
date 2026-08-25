"""Office endpoint tests for validation, errors, and cleanup."""

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import libreoffice_service


def _docx_bytes(*, valid_document_xml: bool = True) -> bytes:
    output = BytesIO()
    document_xml = b'<w:document xmlns:w="urn:test"/>'

    if not valid_document_xml:
        document_xml = b"<broken"

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            b'<Types xmlns="urn:test"/>',
        )
        archive.writestr(
            "_rels/.rels",
            b'<Relationships xmlns="urn:test"/>',
        )
        archive.writestr("word/document.xml", document_xml)

    return output.getvalue()


def _assert_temp_dirs_empty(*directories: Path) -> None:
    for directory in directories:
        assert list(directory.iterdir()) == []


@pytest.fixture()
def convert_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)
    monkeypatch.setattr(settings, "cleanup_mode", "immediate")

    def fake_convert_to_pdf(input_path: Path, job_id: str) -> Path:
        job_output_dir = output_dir / job_id
        job_output_dir.mkdir()
        output_path = job_output_dir / f"{input_path.stem}.pdf"
        output_path.write_bytes(b"%PDF-1.4\n%%EOF")
        return output_path

    monkeypatch.setattr(
        libreoffice_service,
        "convert_to_pdf",
        fake_convert_to_pdf,
    )

    with TestClient(app) as client:
        yield client, upload_dir, output_dir

    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_docx_endpoint_converts_valid_package_and_cleans_temp(convert_client) -> None:
    client, upload_dir, output_dir = convert_client

    response = client.post(
        "/api/convert/docx-to-pdf",
        files={
            "file": (
                "private report.docx",
                _docx_bytes(),
                (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert "private_report.pdf" in response.headers["content-disposition"]
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_docx_endpoint_rejects_malformed_xml_before_conversion(
    convert_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = convert_client
    conversion_called = False

    def fail_if_called(*args, **kwargs):
        nonlocal conversion_called
        conversion_called = True
        raise AssertionError("LibreOffice must not receive malformed input")

    monkeypatch.setattr(libreoffice_service, "convert_to_pdf", fail_if_called)

    response = client.post(
        "/api/convert/docx-to-pdf",
        files={
            "file": (
                "broken.docx",
                _docx_bytes(valid_document_xml=False),
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "corrupted_file"
    assert conversion_called is False
    _assert_temp_dirs_empty(upload_dir, output_dir)


@pytest.mark.parametrize("file_count", [0, 2])
def test_docx_endpoint_requires_exactly_one_file(
    convert_client,
    file_count: int,
) -> None:
    client, upload_dir, output_dir = convert_client
    files = [
        (
            "file",
            (f"document-{index}.docx", _docx_bytes(), "application/octet-stream"),
        )
        for index in range(file_count)
    ]

    response = client.post("/api/convert/docx-to-pdf", files=files)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
    _assert_temp_dirs_empty(upload_dir, output_dir)


def test_unknown_endpoint_uses_consistent_error_shape(convert_client) -> None:
    client, _, _ = convert_client

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "The requested API endpoint was not found.",
    }
