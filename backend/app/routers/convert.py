"""Office document-to-PDF endpoints."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import ConversionError, PrivConError, ValidationError
from app.core.file_utils import new_job_id, sanitize_filename, save_upload_to_temp
from app.core.logging_config import log_job_event
from app.core.security import LimitedUploadRoute
from app.core.validators import (
    validate_extension,
    validate_office_structure,
    validate_pdf_extension,
    validate_pdf_structure,
)
from app.models.schemas import ErrorResponse
from app.services import libreoffice_service
from app.services.cleanup_service import (
    cleanup_after_response,
    cleanup_now,
    mark_active_paths,
)
from app.services.pdf_to_word_service import pdf_to_docx, validate_pdf_to_word_mode

router = APIRouter(
    prefix="/api/convert",
    tags=["convert"],
    route_class=LimitedUploadRoute,
)
logger = logging.getLogger("privcon.jobs")


def _error_response(status_code: int, error: PrivConError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error.code,
            message=error.message,
        ).model_dump(),
    )


def _handle_office_conversion(
    tool_key: str,
    job_id: str,
    upload: UploadFile,
    background_tasks: BackgroundTasks,
) -> Response:
    tool_name = f"{tool_key}-to-pdf"
    original_filename = upload.filename or "upload"
    input_path: Path | None = None
    output_path: Path | None = None

    try:
        validate_extension(original_filename, tool_key)
        input_path = save_upload_to_temp(
            source=upload.file,
            upload_dir=settings.upload_temp_dir,
            job_id=job_id,
            original_filename=original_filename,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
        mark_active_paths([input_path])
        validate_office_structure(input_path, tool_key)
        output_path = libreoffice_service.convert_to_pdf(input_path, job_id)
    except ValidationError as exc:
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(400, exc)
    except ConversionError as exc:
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        status_code = {
            "backend_unavailable": 503,
            "conversion_timeout": 504,
        }.get(exc.code, 422)
        return _error_response(status_code, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(
            500,
            ConversionError(
                code="file_processing_failed",
                message="The uploaded document could not be processed.",
            ),
        )

    if input_path is None or output_path is None:
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(
            500,
            ConversionError(
                code="conversion_failed",
                message="The document could not be converted to PDF.",
            ),
        )

    background_tasks.add_task(
        cleanup_after_response,
        [input_path, output_path.parent],
    )

    safe_stem = sanitize_filename(Path(original_filename).stem).strip(".")
    download_name = f"{safe_stem or 'document'}.pdf"
    log_job_event(logger, tool=tool_name, job_id=job_id, status="success")

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=download_name,
        background=background_tasks,
    )


def _convert_endpoint(
    tool_key: str,
    files: list[UploadFile] | None,
    background_tasks: BackgroundTasks,
) -> Response:
    job_id = new_job_id()
    tool_name = f"{tool_key}-to-pdf"
    log_job_event(logger, tool=tool_name, job_id=job_id, status="started")

    if not files or len(files) != 1:
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(
            400,
            ValidationError(
                code="invalid_input",
                message="Upload exactly one document to convert.",
            ),
        )

    return _handle_office_conversion(
        tool_key,
        job_id,
        files[0],
        background_tasks,
    )


def _handle_pdf_to_word_conversion(
    upload: UploadFile,
    background_tasks: BackgroundTasks,
    mode: str | None,
) -> Response:
    job_id = new_job_id()
    tool_name = "pdf-to-docx"
    original_filename = upload.filename or "upload"
    input_path: Path | None = None
    output_path: Path | None = None
    log_job_event(logger, tool=tool_name, job_id=job_id, status="started")

    try:
        validate_pdf_extension(original_filename)
        input_path = save_upload_to_temp(
            source=upload.file,
            upload_dir=settings.upload_temp_dir,
            job_id=job_id,
            original_filename=original_filename,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )
        mark_active_paths([input_path])
        validate_pdf_structure(input_path)
        selected_mode = validate_pdf_to_word_mode(mode)
        output_path = pdf_to_docx(input_path, job_id, mode=selected_mode)
    except ValidationError as exc:
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(400, exc)
    except ConversionError as exc:
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(422, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        cleanup_now([input_path] if input_path is not None else [])
        log_job_event(logger, tool=tool_name, job_id=job_id, status="failure")
        return _error_response(
            500,
            ConversionError(
                code="file_processing_failed",
                message="The uploaded PDF could not be processed.",
            ),
        )

    background_tasks.add_task(
        cleanup_after_response,
        [input_path, output_path.parent],
    )
    safe_stem = sanitize_filename(Path(original_filename).stem).strip(".")
    log_job_event(logger, tool=tool_name, job_id=job_id, status="success")

    return FileResponse(
        path=output_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=f"{safe_stem or 'document'}.docx",
        background=background_tasks,
    )


@router.post("/docx-to-pdf")
def docx_to_pdf(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
) -> Response:
    return _convert_endpoint("docx", files, background_tasks)


@router.post("/pdf-to-docx")
def pdf_to_word(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
    mode: Annotated[str | None, Form()] = None,
) -> Response:
    if not files or len(files) != 1:
        error = ValidationError(
            code="invalid_input",
            message="Upload exactly one PDF to convert.",
        )
        return _error_response(400, error)

    return _handle_pdf_to_word_conversion(files[0], background_tasks, mode)


@router.post("/pptx-to-pdf")
def pptx_to_pdf(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
) -> Response:
    return _convert_endpoint("pptx", files, background_tasks)


@router.post("/xlsx-to-pdf")
def xlsx_to_pdf(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="file")] = None,
) -> Response:
    return _convert_endpoint("xlsx", files, background_tasks)
