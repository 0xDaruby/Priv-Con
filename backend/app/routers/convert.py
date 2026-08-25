"""Office document-to-PDF endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import ConversionError, PrivConError, ValidationError
from app.core.file_utils import new_job_id, sanitize_filename, save_upload_to_temp
from app.core.logging_config import log_job_event
from app.core.validators import validate_extension, validate_office_structure
from app.models.schemas import ErrorResponse
from app.services import libreoffice_service
from app.services.cleanup_service import (
    cleanup_after_response,
    cleanup_now,
    mark_active_paths,
)


router = APIRouter(prefix="/api/convert", tags=["convert"])
logger = logging.getLogger("privcon.jobs")


def _error_response(status_code: int, error: PrivConError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error.code,
            message=error.message,
        ).model_dump(),
    )


async def _handle_office_conversion(
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
    except Exception:
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


async def _convert_endpoint(
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

    return await _handle_office_conversion(
        tool_key,
        job_id,
        files[0],
        background_tasks,
    )


@router.post("/docx-to-pdf")
async def docx_to_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None = File(default=None, alias="file"),
) -> Response:
    return await _convert_endpoint("docx", files, background_tasks)


@router.post("/pptx-to-pdf")
async def pptx_to_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None = File(default=None, alias="file"),
) -> Response:
    return await _convert_endpoint("pptx", files, background_tasks)


@router.post("/xlsx-to-pdf")
async def xlsx_to_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None = File(default=None, alias="file"),
) -> Response:
    return await _convert_endpoint("xlsx", files, background_tasks)
