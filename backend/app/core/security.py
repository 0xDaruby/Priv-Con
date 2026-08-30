"""Request-level safeguards for PrivCon's local upload API."""

from __future__ import annotations

import threading
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.models.schemas import ErrorResponse

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, message=message).model_dump(),
    )


class LimitedUploadRoute(APIRoute):
    """Parse multipart bodies with strict file/field-count limits."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Any]]:
        route_handler = super().get_route_handler()

        async def limited_route_handler(request: Request) -> Any:
            content_type = request.headers.get("content-type", "").lower()

            if content_type.startswith("multipart/form-data"):
                await request.form(
                    max_files=settings.max_files_per_request,
                    max_fields=settings.max_form_fields_per_request,
                    max_part_size=settings.max_form_field_size_kb * 1024,
                )

            return await route_handler(request)

        return limited_route_handler


class RequestBodyLimitMiddleware:
    """Reject oversized bodies before multipart parsing and temp spooling."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = settings.max_request_size_mb * 1024 * 1024
        content_length = _content_length(scope)

        if content_length is not None and content_length > limit:
            response = _error_response(
                413,
                "oversized_request",
                (
                    "The request body exceeds the "
                    f"{settings.max_request_size_mb} MB limit."
                ),
            )
            await response(scope, receive, send)
            return

        received = 0

        async def receive_with_limit() -> Message:
            nonlocal received
            message = await receive()

            if message["type"] == "http.request":
                received += len(message.get("body", b""))

                if received > limit:
                    raise _RequestBodyTooLarge

            return message

        try:
            await self.app(scope, receive_with_limit, send)
        except _RequestBodyTooLarge:
            response = _error_response(
                413,
                "oversized_request",
                (
                    "The request body exceeds the "
                    f"{settings.max_request_size_mb} MB limit."
                ),
            )
            await response(scope, receive, send)


class UploadOriginMiddleware:
    """Block browser cross-site writes while preserving local CLI clients."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return

        headers = _headers(scope)
        origin = headers.get("origin")
        fetch_site = headers.get("sec-fetch-site", "").lower()
        allowed_origin = settings.cors_origin.rstrip("/")

        if (
            origin is not None and origin.rstrip("/") != allowed_origin
        ) or fetch_site == "cross-site":
            response = _error_response(
                403,
                "origin_not_allowed",
                "Cross-site upload requests are not allowed.",
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class ProcessingConcurrencyMiddleware:
    """Bound simultaneous upload jobs, including parsing and streaming."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._active_jobs = 0
        self._lock = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        is_job = (
            scope["type"] == "http"
            and scope["method"] in _UNSAFE_METHODS - {"DELETE"}
            and scope.get("path", "").startswith("/api/")
        )

        if not is_job:
            await self.app(scope, receive, send)
            return

        with self._lock:
            if self._active_jobs >= settings.max_concurrent_jobs:
                accepted = False
            else:
                self._active_jobs += 1
                accepted = True

        if not accepted:
            response = _error_response(
                503,
                "server_busy",
                "The local converter is busy. Please retry shortly.",
            )
            await response(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        finally:
            with self._lock:
                self._active_jobs -= 1


class SecurityHeadersMiddleware:
    """Prevent API/download caching and browser content-type sniffing."""

    _HEADERS = (
        (b"cache-control", b"no-store"),
        (b"pragma", b"no-cache"),
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-frame-options", b"DENY"),
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                headers.extend(
                    header for header in self._HEADERS if header[0] not in existing
                )
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


class _RequestBodyTooLarge(BaseException):
    """Private control-flow signal that bypasses application handlers."""


def _headers(scope: Scope) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }


def _content_length(scope: Scope) -> int | None:
    raw_value = _headers(scope).get("content-length")

    if raw_value is None:
        return None

    try:
        value = int(raw_value)
    except ValueError:
        return None

    return value if value >= 0 else None
