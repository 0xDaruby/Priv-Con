"""Cross-cutting request, privacy, and filesystem security tests."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.exceptions import ValidationError
from app.core.file_utils import (
    enforce_output_size,
    private_binary_writer,
    sanitize_filename,
)
from app.core.security import (
    ProcessingConcurrencyMiddleware,
    RequestBodyLimitMiddleware,
)
from app.main import app
from app.services.cleanup_service import cleanup_now


@pytest.fixture()
def security_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)

    with TestClient(app) as client:
        yield client, upload_dir, output_dir


def test_request_body_limit_rejects_before_endpoint(
    security_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = security_client
    monkeypatch.setattr(settings, "max_request_size_mb", 1)

    response = client.post(
        "/api/images/to-pdf",
        content=b"x" * (1024 * 1024 + 1),
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "error": "oversized_request",
        "message": "The request body exceeds the 1 MB limit.",
    }
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []


def test_streamed_body_without_content_length_is_still_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_request_size_mb", 1)
    sent_messages = []
    request_messages = iter(
        [
            {
                "type": "http.request",
                "body": b"a" * 600_000,
                "more_body": True,
            },
            {
                "type": "http.request",
                "body": b"b" * 600_000,
                "more_body": False,
            },
        ]
    )

    async def receive():
        return next(request_messages)

    async def send(message):
        sent_messages.append(message)

    async def consume_body(scope, receive, send):
        while True:
            message = await receive()

            if not message.get("more_body", False):
                break

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/images/to-pdf",
        "raw_path": b"/api/images/to-pdf",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "root_path": "",
    }

    asyncio.run(RequestBodyLimitMiddleware(consume_body)(scope, receive, send))

    start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    body = next(
        message for message in sent_messages if message["type"] == "http.response.body"
    )
    assert start["status"] == 413
    assert json.loads(body["body"])["error"] == "oversized_request"


def test_concurrent_jobs_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_concurrent_jobs", 1)
    first_messages = []
    second_messages = []

    async def exercise_limit() -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_job(scope, receive, send):
            started.set()
            await release.wait()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = ProcessingConcurrencyMiddleware(slow_job)
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/pdf/merge",
            "raw_path": b"/api/pdf/merge",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 123),
            "root_path": "",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send_first(message):
            first_messages.append(message)

        async def send_second(message):
            second_messages.append(message)

        first_job = asyncio.create_task(middleware(scope, receive, send_first))
        await started.wait()
        await middleware(scope, receive, send_second)
        release.set()
        await first_job

    asyncio.run(exercise_limit())

    second_start = next(
        message
        for message in second_messages
        if message["type"] == "http.response.start"
    )
    second_body = next(
        message
        for message in second_messages
        if message["type"] == "http.response.body"
    )
    assert second_start["status"] == 503
    assert json.loads(second_body["body"])["error"] == "server_busy"
    assert any(message["type"] == "http.response.start" for message in first_messages)


def test_multipart_file_count_is_limited_before_processing(
    security_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, upload_dir, output_dir = security_client
    monkeypatch.setattr(settings, "max_files_per_request", 1)

    response = client.post(
        "/api/images/to-pdf",
        files=[
            ("files", ("one.png", b"not-read", "image/png")),
            ("files", ("two.png", b"not-read", "image/png")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
    assert list(upload_dir.iterdir()) == []
    assert list(output_dir.iterdir()) == []


def test_cross_site_uploads_are_rejected_with_consistent_shape(
    security_client,
) -> None:
    client, _, _ = security_client

    response = client.post(
        "/api/images/to-pdf",
        headers={
            "origin": "https://attacker.example",
            "sec-fetch-site": "cross-site",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": "origin_not_allowed",
        "message": "Cross-site upload requests are not allowed.",
    }


def test_api_responses_disable_caching_and_sniffing(security_client) -> None:
    client, _, _ = security_client

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"


def test_filename_sanitization_handles_both_path_styles_and_length() -> None:
    assert sanitize_filename(r"C:\private\..\report?.pdf") == "report_.pdf"
    long_name = sanitize_filename(f"{'a' * 300}.pdf")
    assert len(long_name) <= 128
    assert long_name.endswith(".pdf")


def test_private_writer_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    output_path = tmp_path / "existing.pdf"
    output_path.write_bytes(b"private")

    with pytest.raises(FileExistsError), private_binary_writer(output_path):
        pass

    assert output_path.read_bytes() == b"private"


def test_cleanup_refuses_paths_outside_configured_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()
    outside_path = tmp_path / "keep.txt"
    outside_path.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(settings, "upload_temp_dir", upload_dir)
    monkeypatch.setattr(settings, "output_temp_dir", output_dir)

    cleanup_now([outside_path])

    assert outside_path.read_text(encoding="utf-8") == "keep"


def test_generated_output_size_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "large.pdf"
    output_path.write_bytes(b"x" * (1024 * 1024 + 1))
    monkeypatch.setattr(settings, "max_output_size_mb", 1)

    with pytest.raises(ValidationError) as exc_info:
        enforce_output_size(output_path)

    assert exc_info.value.code == "output_too_large"
