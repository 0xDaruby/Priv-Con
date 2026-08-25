"""PDF utility endpoints."""

from pathlib import Path
from typing import Sequence

from fastapi import APIRouter, BackgroundTasks, File, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import PrivConError, ValidationError
from app.core.file_utils import cleanup_paths, new_job_id, save_upload_to_temp
from app.core.validators import validate_pdf_extension, validate_pdf_structure
from app.models.schemas import ErrorResponse
from app.services.pdf_merge_service import MergeError, merge_pdfs


router = APIRouter(prefix="/api/pdf", tags=["pdf"])


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

    cleanup_paths(cleanup_targets)


@router.post("/merge")
async def merge_pdf_endpoint(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None = File(default=None),
) -> Response:
    if not files or len(files) < 2:
        return _error_response(
            400,
            ValidationError(
                code="invalid_input",
                message="Upload at least two PDF files to merge.",
            ),
        )

    saved_paths: list[Path] = []
    output_path: Path | None = None

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
            )
            saved_paths.append(path)
            validate_pdf_structure(path)

        output_path = merge_pdfs(saved_paths)
    except ValidationError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        return _error_response(400, exc)
    except MergeError as exc:
        _cleanup_after_failure(saved_paths, output_path)
        return _error_response(422, exc)
    except Exception:
        _cleanup_after_failure(saved_paths, output_path)
        return _error_response(
            500,
            MergeError(
                code="file_processing_failed",
                message="The uploaded files could not be processed.",
            ),
        )

    if output_path is None:
        _cleanup_after_failure(saved_paths, output_path)
        return _error_response(
            500,
            MergeError(
                code="conversion_failed",
                message="Failed to merge PDF files.",
            ),
        )

    background_tasks.add_task(
        cleanup_paths,
        [*saved_paths, output_path.parent],
    )

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="merged.pdf",
        background=background_tasks,
    )
