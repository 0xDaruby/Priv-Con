"""Asynchronous local conversion jobs with truthful progress reporting."""

from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import (
    JobCapacityError,
    JobLookupError,
    PrivConError,
    ValidationError,
)
from app.core.file_utils import (
    enforce_total_upload_size,
    new_job_id,
    save_upload_to_temp,
)
from app.core.security import LimitedUploadRoute
from app.core.validators import (
    validate_extension,
    validate_image_extension,
    validate_pdf_extension,
)
from app.models.schemas import ErrorResponse, JobStatusResponse
from app.services.cleanup_service import mark_active_paths
from app.services.job_service import (
    JobSnapshot,
    JobSpec,
    JobTool,
    job_manager,
)
from app.services.pdf_split_service import SplitError, validate_split_options

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    route_class=LimitedUploadRoute,
)

JOB_TOOLS: frozenset[str] = frozenset(
    {
        "docx-to-pdf",
        "pptx-to-pdf",
        "xlsx-to-pdf",
        "pdf-merge",
        "pdf-split",
        "images-to-pdf",
    }
)


def _error_response(status_code: int, error: PrivConError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error.code, message=error.message).model_dump(),
    )


def _status_response(snapshot: JobSnapshot) -> JobStatusResponse:
    error = None

    if snapshot.error_code is not None and snapshot.error_message is not None:
        error = ErrorResponse(
            error=snapshot.error_code,
            message=snapshot.error_message,
        )

    return JobStatusResponse(
        job_id=snapshot.job_id,
        tool=snapshot.tool,
        status=snapshot.status,
        stage=snapshot.stage,
        message=snapshot.message,
        progress_percent=snapshot.progress_percent,
        completed_units=snapshot.completed_units,
        total_units=snapshot.total_units,
        unit_label=snapshot.unit_label,
        result_available=snapshot.result_available,
        result_filename=snapshot.result_filename,
        result_content_type=snapshot.result_content_type,
        error=error,
    )


def _select_uploads(
    tool: JobTool,
    single_files: list[UploadFile] | None,
    multiple_files: list[UploadFile] | None,
) -> list[UploadFile]:
    if tool in {"docx-to-pdf", "pptx-to-pdf", "xlsx-to-pdf", "pdf-split"}:
        if multiple_files or not single_files or len(single_files) != 1:
            raise ValidationError(
                code="invalid_input",
                message="Upload exactly one file for this conversion.",
            )
        return single_files

    if single_files:
        raise ValidationError(
            code="invalid_input",
            message="Use the ordered files field for this conversion.",
        )

    if tool == "pdf-merge" and (not multiple_files or len(multiple_files) < 2):
        raise ValidationError(
            code="invalid_input",
            message="Upload at least two PDF files to merge.",
        )

    if tool == "images-to-pdf" and not multiple_files:
        raise ValidationError(
            code="invalid_input",
            message="Upload at least one image to convert.",
        )

    return multiple_files or []


def _validate_filename(tool: JobTool, filename: str) -> None:
    office_tool_keys = {
        "docx-to-pdf": "docx",
        "pptx-to-pdf": "pptx",
        "xlsx-to-pdf": "xlsx",
    }

    if tool in office_tool_keys:
        validate_extension(filename, office_tool_keys[tool])
    elif tool in {"pdf-merge", "pdf-split"}:
        validate_pdf_extension(filename)
    else:
        validate_image_extension(filename)


@router.post("/{tool}", status_code=202, response_model=JobStatusResponse)
def create_job(
    tool: str,
    single_files: Annotated[
        list[UploadFile] | None,
        File(alias="file"),
    ] = None,
    multiple_files: Annotated[
        list[UploadFile] | None,
        File(alias="files"),
    ] = None,
    mode: Annotated[str | None, Form()] = None,
    ranges: Annotated[str | None, Form()] = None,
) -> Response:
    if tool not in JOB_TOOLS:
        return _error_response(
            404,
            JobLookupError(
                code="not_found",
                message="The requested conversion tool was not found.",
            ),
        )

    selected_tool = cast(JobTool, tool)

    try:
        uploads = _select_uploads(selected_tool, single_files, multiple_files)

        if selected_tool == "pdf-split":
            validate_split_options((mode or "").strip(), ranges)
    except (ValidationError, SplitError) as exc:
        return _error_response(400, exc)

    try:
        job_id = job_manager.reserve(selected_tool)
    except JobCapacityError as exc:
        return _error_response(503, exc)

    saved_paths: list[Path] = []
    original_filenames: list[str] = []
    total_upload_bytes = 0

    try:
        for upload in uploads:
            original_filename = upload.filename or "upload"
            _validate_filename(selected_tool, original_filename)
            saved_path = save_upload_to_temp(
                source=upload.file,
                upload_dir=settings.upload_temp_dir,
                job_id=new_job_id(),
                original_filename=original_filename,
                max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
            )
            saved_paths.append(saved_path)
            original_filenames.append(original_filename)
            mark_active_paths([saved_path])
            total_upload_bytes += saved_path.stat().st_size
            enforce_total_upload_size(total_upload_bytes)

        snapshot = job_manager.start(
            job_id,
            JobSpec(
                tool=selected_tool,
                input_paths=tuple(saved_paths),
                original_filenames=tuple(original_filenames),
                mode=(mode or "").strip() or None,
                ranges=ranges,
            ),
        )
        return JSONResponse(
            status_code=202,
            content=_status_response(snapshot).model_dump(),
        )
    except ValidationError as exc:
        job_manager.discard_submission(job_id, tuple(saved_paths))
        return _error_response(400, exc)
    except Exception:  # noqa: BLE001 - normalize the upload trust boundary.
        job_manager.discard_submission(job_id, tuple(saved_paths))
        return _error_response(
            500,
            ValidationError(
                code="file_processing_failed",
                message="The selected files could not be prepared for processing.",
            ),
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> Response:
    try:
        return JSONResponse(
            content=_status_response(job_manager.get(job_id)).model_dump()
        )
    except JobLookupError as exc:
        return _error_response(404, exc)


@router.delete("/{job_id}", response_model=JobStatusResponse)
def cancel_job(job_id: str) -> Response:
    try:
        return JSONResponse(
            content=_status_response(job_manager.cancel(job_id)).model_dump()
        )
    except JobLookupError as exc:
        return _error_response(404, exc)


@router.get("/{job_id}/result")
def get_job_result(job_id: str, background_tasks: BackgroundTasks) -> Response:
    try:
        result = job_manager.claim_result(job_id)
    except JobLookupError as exc:
        status_code = 404 if exc.code == "not_found" else 409
        if exc.code == "result_unavailable":
            status_code = 410
        return _error_response(status_code, exc)

    background_tasks.add_task(job_manager.mark_result_delivered, job_id)

    try:
        return FileResponse(
            path=result.path,
            # A private transport MIME prevents browser download-manager
            # extensions from intercepting this internal fetch. The real MIME
            # and filename are supplied by the validated local job snapshot and
            # restored on the frontend Blob.
            media_type="application/x-privcon-result",
            background=background_tasks,
        )
    except Exception:
        job_manager.release_result_claim(job_id)
        raise
