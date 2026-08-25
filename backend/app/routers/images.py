"""Image utility endpoints."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import (
    enforce_total_upload_size,
    new_job_id,
    save_upload_to_temp,
)
from app.core.logging_config import log_job_event
from app.core.security import LimitedUploadRoute
from app.core.validators import validate_image_extension, validate_image_structure
from app.models.schemas import ErrorResponse
from app.services.cleanup_service import (
    cleanup_after_response,
    cleanup_now,
    mark_active_paths,
)
from app.services.image_service import ImageConversionError, images_to_pdf

router = APIRouter(
    prefix="/api/images",
    tags=["images"],
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


@router.post("/to-pdf")
def images_to_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> Response:
    job_id = new_job_id()
    log_job_event(logger, tool="images-to-pdf", job_id=job_id, status="started")

    if not files:
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id=job_id,
            status="failure",
        )
        return _error_response(
            400,
            ValidationError(
                code="invalid_input",
                message="Upload at least one image to convert.",
            ),
        )

    saved_paths: list[Path] = []
    output_path: Path | None = None
    total_upload_bytes = 0
    total_pixels = 0

    try:
        # Multipart order is the requested PDF page order.
        for upload in files:
            original_filename = upload.filename or "upload"
            validate_image_extension(original_filename)

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
            total_pixels += validate_image_structure(path, original_filename)

            if total_pixels > settings.max_total_image_pixels:
                raise ValidationError(
                    code="oversized_file",
                    message=(
                        "The combined image dimensions exceed safe processing limits."
                    ),
                )

        output_path = images_to_pdf(saved_paths)
    except ValidationError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id=job_id,
            status="failure",
        )
        return _error_response(400, exc)
    except ImageConversionError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id=job_id,
            status="failure",
        )
        return _error_response(422, exc)
    except Exception:  # noqa: BLE001 - cleanup at the API trust boundary.
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id=job_id,
            status="failure",
        )
        return _error_response(
            500,
            ImageConversionError(
                code="file_processing_failed",
                message="The uploaded images could not be processed.",
            ),
        )

    if output_path is None:
        _cleanup_after_failure(saved_paths, output_path)
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id=job_id,
            status="failure",
        )
        return _error_response(
            500,
            ImageConversionError(
                code="conversion_failed",
                message="The images could not be converted to PDF.",
            ),
        )

    background_tasks.add_task(
        cleanup_after_response,
        [*saved_paths, output_path.parent],
    )
    log_job_event(
        logger,
        tool="images-to-pdf",
        job_id=job_id,
        status="success",
    )

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="images.pdf",
        background=background_tasks,
    )


def _cleanup_after_failure(
    saved_paths: list[Path],
    output_path: Path | None,
) -> None:
    cleanup_targets = list(saved_paths)

    if output_path is not None:
        cleanup_targets.append(output_path.parent)

    cleanup_now(cleanup_targets)
