"""PDF utility endpoints."""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import (
    enforce_total_upload_size,
    new_job_id,
    sanitize_filename,
    save_upload_to_temp,
)
from app.core.logging_config import log_job_event
from app.core.security import LimitedUploadRoute
from app.core.validators import (
    validate_image_extension,
    validate_pdf_extension,
    validate_pdf_structure,
)
from app.models.schemas import ErrorResponse
from app.services.cleanup_service import (
    cleanup_after_response,
    cleanup_now,
    mark_active_paths,
)
from app.services.pdf_merge_service import MergeError, merge_pdfs
from app.services.pdf_overlay_options import (
    PageNumberOptions,
    WatermarkOptions,
    overlay_options,
    validate_overlay_image_choice,
)
from app.services.pdf_page_numbers_service import add_page_numbers
from app.services.pdf_rotate_service import rotate_pdf
from app.services.pdf_split_service import (
    SplitError,
    split_pdf,
    validate_split_options,
)
from app.services.pdf_to_image_service import pdf_to_jpeg
from app.services.pdf_tool_options import (
    JpegOptions,
    RotateOptions,
    jpeg_options,
    rotation_options,
)
from app.services.pdf_watermark_service import watermark_pdf

router = APIRouter(
    prefix="/api/pdf",
    tags=["pdf"],
    route_class=LimitedUploadRoute,
)
logger = logging.getLogger("privcon.jobs")


def _single_pdf_tool(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None,
    options: RotateOptions | JpegOptions,
) -> Response:
    tool = "pdf-rotate" if isinstance(options, RotateOptions) else "pdf-to-jpg"
    job_id = new_job_id()
    saved_path: Path | None = None
    output_path: Path | None = None
    log_job_event(logger, tool=tool, job_id=job_id, status="started")
    try:
        if not files or len(files) != 1:
            raise ValidationError("invalid_input", "Upload exactly one PDF file.")
        upload = files[0]
        filename = upload.filename or "upload"
        validate_pdf_extension(filename)
        saved_path = save_upload_to_temp(
            source=upload.file,
            upload_dir=settings.upload_temp_dir,
            job_id=new_job_id(),
            original_filename=filename,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
        mark_active_paths([saved_path])
        enforce_total_upload_size(saved_path.stat().st_size)
        validate_pdf_structure(saved_path)
        if isinstance(options, RotateOptions):
            output_path = rotate_pdf(saved_path, options)
            media_type = "application/pdf"
            stem = Path(sanitize_filename(filename)).stem.strip(".")[:100] or "document"
            download_name = f"{stem}_rotated.pdf"
        else:
            result = pdf_to_jpeg(saved_path, filename, options)
            output_path = result.path
            media_type = result.media_type
            download_name = result.download_name
    except PrivConError as exc:
        _cleanup_after_failure([saved_path] if saved_path else [], output_path)
        log_job_event(logger, tool=tool, job_id=job_id, status="failure")
        return _error_response(400 if isinstance(exc, ValidationError) else 422, exc)
    except Exception:  # noqa: BLE001 - normalize errors and clean at upload boundary.
        _cleanup_after_failure([saved_path] if saved_path else [], output_path)
        log_job_event(logger, tool=tool, job_id=job_id, status="failure")
        return _error_response(
            500,
            PrivConError("file_processing_failed", "The PDF could not be processed."),
        )
    background_tasks.add_task(cleanup_after_response, [saved_path, output_path.parent])
    log_job_event(logger, tool=tool, job_id=job_id, status="success")
    return FileResponse(
        output_path,
        media_type=media_type,
        filename=download_name,
        background=background_tasks,
    )


@router.post("/rotate")
def rotate_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    pages: Annotated[str | None, Form()] = None,
    angle: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        options = rotation_options(pages, angle)
    except ValidationError as exc:
        return _error_response(400, exc)
    return _single_pdf_tool(background_tasks, files, options)


@router.post("/to-jpg")
def pdf_to_jpg_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    pages: Annotated[str | None, Form()] = None,
    dpi: Annotated[str | None, Form()] = None,
    quality: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        options = jpeg_options(pages, dpi, quality)
    except ValidationError as exc:
        return _error_response(400, exc)
    return _single_pdf_tool(background_tasks, files, options)


def _overlay_pdf_tool(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None,
    images: list[UploadFile] | None,
    options: WatermarkOptions | PageNumberOptions,
) -> Response:
    saved_paths: list[Path] = []
    output: Path | None = None
    try:
        if not files or len(files) != 1:
            raise ValidationError("invalid_input", "Upload exactly one PDF file.")
        validate_overlay_image_choice(options, len(images or []))
        uploads = [*files, *(images or [])]
        total_bytes = 0
        for index, upload in enumerate(uploads):
            filename = upload.filename or "upload"
            if index == 0:
                validate_pdf_extension(filename)
            else:
                validate_image_extension(filename)
            path = save_upload_to_temp(
                source=upload.file,
                upload_dir=settings.upload_temp_dir,
                job_id=new_job_id(),
                original_filename=filename,
                max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
            )
            saved_paths.append(path)
            mark_active_paths([path])
            total_bytes += path.stat().st_size
            enforce_total_upload_size(total_bytes)
        if isinstance(options, WatermarkOptions):
            output = watermark_pdf(
                saved_paths[0],
                options,
                saved_paths[1] if len(saved_paths) == 2 else None,
            )
            suffix = "watermarked"
        else:
            output = add_page_numbers(saved_paths[0], options)
            suffix = "numbered"
        stem = (
            Path(sanitize_filename(files[0].filename or "document")).stem.strip(".")[
                :100
            ]
            or "document"
        )
        background_tasks.add_task(cleanup_after_response, [*saved_paths, output.parent])
        return FileResponse(
            output,
            media_type="application/pdf",
            filename=f"{stem}_{suffix}.pdf",
            background=background_tasks,
        )
    except PrivConError as exc:
        _cleanup_after_failure(saved_paths, output)
        return _error_response(400 if isinstance(exc, ValidationError) else 422, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        _cleanup_after_failure(saved_paths, output)
        return _error_response(
            500,
            PrivConError(
                "file_processing_failed", "The PDF overlay could not be processed."
            ),
        )


@router.post("/watermark")
def watermark_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    images: Annotated[list[UploadFile] | None, File(alias="watermark_image")] = None,
    pages: Annotated[str | None, Form()] = None,
    options: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        parsed = overlay_options("pdf-watermark", pages, options)
    except ValidationError as exc:
        return _error_response(400, exc)
    return _overlay_pdf_tool(background_tasks, files, images, parsed)


@router.post("/page-numbers")
def page_numbers_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    images: Annotated[list[UploadFile] | None, File(alias="watermark_image")] = None,
    pages: Annotated[str | None, Form()] = None,
    options: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        parsed = overlay_options("pdf-page-numbers", pages, options)
    except ValidationError as exc:
        return _error_response(400, exc)
    return _overlay_pdf_tool(background_tasks, files, images, parsed)


def _error_response(status_code: int, error: PrivConError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error.code,
            message=error.message,
        ).model_dump(),
    )


def _cleanup_after_failure(
    saved_paths: Sequence[Path],
    output_path: Path | None,
) -> None:
    cleanup_targets = list(saved_paths)

    if output_path is not None:
        cleanup_targets.append(output_path.parent)

    cleanup_now(cleanup_targets)


@router.post("/merge")
def merge_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> Response:
    job_id = new_job_id()
    log_job_event(logger, tool="pdf-merge", job_id=job_id, status="started")

    if not files or len(files) < 2:
        log_job_event(logger, tool="pdf-merge", job_id=job_id, status="failure")
        return _error_response(
            400,
            ValidationError(
                code="invalid_input",
                message="Upload at least two PDF files to merge.",
            ),
        )

    saved_paths: list[Path] = []
    output_path: Path | None = None
    total_upload_bytes = 0
    total_pages = 0

    try:
        # Multipart order is the requested merge order.
        for upload in files:
            original_filename = upload.filename or "upload"
            validate_pdf_extension(original_filename)

            path = save_upload_to_temp(
                source=upload.file,
                upload_dir=settings.upload_temp_dir,
                job_id=new_job_id(),
                original_filename=original_filename,
                max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
            )
            saved_paths.append(path)
            mark_active_paths([path])
            total_upload_bytes += path.stat().st_size
            enforce_total_upload_size(total_upload_bytes)
            total_pages += validate_pdf_structure(path)

            if total_pages > settings.max_pdf_pages_per_job:
                raise ValidationError(
                    code="too_many_pages",
                    message=(
                        "The combined PDFs exceed the safe page-count limit of "
                        f"{settings.max_pdf_pages_per_job} pages."
                    ),
                )

        output_path = merge_pdfs(saved_paths)
    except ValidationError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(logger, tool="pdf-merge", job_id=job_id, status="failure")
        return _error_response(400, exc)
    except MergeError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(logger, tool="pdf-merge", job_id=job_id, status="failure")
        return _error_response(422, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(logger, tool="pdf-merge", job_id=job_id, status="failure")
        return _error_response(
            500,
            MergeError(
                code="file_processing_failed",
                message="The uploaded files could not be processed.",
            ),
        )

    if output_path is None:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(logger, tool="pdf-merge", job_id=job_id, status="failure")
        return _error_response(
            500,
            MergeError(
                code="conversion_failed",
                message="Failed to merge PDF files.",
            ),
        )

    background_tasks.add_task(
        cleanup_after_response,
        [*saved_paths, output_path.parent],
    )
    log_job_event(logger, tool="pdf-merge", job_id=job_id, status="success")

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="merged.pdf",
        background=background_tasks,
    )


@router.post("/split")
def split_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    mode: Annotated[str | None, Form()] = None,
    ranges: Annotated[str | None, Form()] = None,
) -> Response:
    job_id = new_job_id()
    log_job_event(logger, tool="pdf-split", job_id=job_id, status="started")

    if not files or len(files) != 1:
        log_job_event(logger, tool="pdf-split", job_id=job_id, status="failure")
        return _error_response(
            400,
            ValidationError(
                code="invalid_input",
                message="Upload exactly one PDF file to split.",
            ),
        )

    file = files[0]
    saved_path: Path | None = None
    output_path: Path | None = None

    try:
        selected_mode = (mode or "").strip()
        validate_split_options(selected_mode, ranges)

        original_filename = file.filename or "upload"
        validate_pdf_extension(original_filename)
        saved_path = save_upload_to_temp(
            source=file.file,
            upload_dir=settings.upload_temp_dir,
            job_id=new_job_id(),
            original_filename=original_filename,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
        mark_active_paths([saved_path])
        enforce_total_upload_size(saved_path.stat().st_size)
        validate_pdf_structure(saved_path)

        result = split_pdf(
            input_path=saved_path,
            original_filename=original_filename,
            mode=selected_mode,
            ranges=ranges,
        )
        output_path = result.path
    except ValidationError as exc:
        _cleanup_after_failure(
            [saved_path] if saved_path is not None else [],
            output_path,
        )
        log_job_event(logger, tool="pdf-split", job_id=job_id, status="failure")
        return _error_response(400, exc)
    except SplitError as exc:
        _cleanup_after_failure(
            [saved_path] if saved_path is not None else [],
            output_path,
        )
        log_job_event(logger, tool="pdf-split", job_id=job_id, status="failure")
        status_code = 400 if exc.code.startswith("invalid_") else 422
        return _error_response(status_code, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        _cleanup_after_failure(
            [saved_path] if saved_path is not None else [],
            output_path,
        )
        log_job_event(logger, tool="pdf-split", job_id=job_id, status="failure")
        return _error_response(
            500,
            SplitError(
                code="file_processing_failed",
                message="The uploaded PDF could not be processed.",
            ),
        )

    if saved_path is None or output_path is None:
        _cleanup_after_failure(
            [saved_path] if saved_path is not None else [],
            output_path,
        )
        log_job_event(logger, tool="pdf-split", job_id=job_id, status="failure")
        return _error_response(
            500,
            SplitError(
                code="split_failed",
                message="The PDF could not be split.",
            ),
        )

    background_tasks.add_task(
        cleanup_after_response,
        [saved_path, output_path.parent],
    )
    log_job_event(logger, tool="pdf-split", job_id=job_id, status="success")

    return FileResponse(
        path=output_path,
        media_type=result.media_type,
        filename=result.download_name,
        background=background_tasks,
    )
