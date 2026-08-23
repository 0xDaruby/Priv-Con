"""
/api/convert/* endpoints: DOCX/PPTX/XLSX -> PDF.

Request flow (all three routes share _handle_office_conversion):
  1. save the upload to a unique temp path
  2. validate extension + ZIP structure (core/validators.py) BEFORE the file
     ever reaches LibreOffice — this is the fix for the "LibreOffice accepts
     garbage input" finding documented in libreoffice-service-notes.md
  3. convert via libreoffice_service.convert_to_pdf()
  4. stream the PDF back, then clean up input + output (CLEANUP_MODE=immediate)

Note: size-limit enforcement (PRD 22.2) is deliberately not here yet — that
lands in Phase 1 step 9 alongside the rest of full validation hardening.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.core.exceptions import ConversionError, ValidationError
from app.core.file_utils import new_job_id, upload_target_path
from app.core.validators import validate_office_file
from app.models.schemas import ErrorResponse
from app.services import libreoffice_service

router = APIRouter(prefix="/api/convert", tags=["convert"])


def _cleanup(*paths: Path) -> None:
    for path in paths:
        if path is None:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)


async def _handle_office_conversion(
    tool_key: str, upload: UploadFile, background_tasks: BackgroundTasks
):
    job_id = new_job_id()
    input_path = upload_target_path(settings.upload_temp_dir, job_id, upload.filename)

    # Save to disk first — both validation and LibreOffice need a real path,
    # not a stream.
    with input_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)

    try:
        validate_office_file(input_path, upload.filename, tool_key)
    except ValidationError as exc:
        _cleanup(input_path)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error=exc.code, message=exc.message).model_dump(),
        )

    try:
        output_path = libreoffice_service.convert_to_pdf(input_path, job_id)
    except ConversionError as exc:
        _cleanup(input_path)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error=exc.code, message=exc.message).model_dump(),
        )

    # Immediate cleanup mode (setup.md section 4 / PRD 21.2): delete temp
    # files right after the response has been sent.
    background_tasks.add_task(_cleanup, input_path, output_path.parent)

    download_name = Path(upload.filename).stem + ".pdf"
    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=download_name,
        background=background_tasks,
    )


@router.post("/docx-to-pdf")
async def docx_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    return await _handle_office_conversion("docx", file, background_tasks)


@router.post("/pptx-to-pdf")
async def pptx_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    return await _handle_office_conversion("pptx", file, background_tasks)


@router.post("/xlsx-to-pdf")
async def xlsx_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    return await _handle_office_conversion("xlsx", file, background_tasks)
