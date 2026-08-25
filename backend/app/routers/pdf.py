import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.core.validators import validate_pdf_structure, ValidationError
from app.core.file_utils import save_upload_to_temp, cleanup_paths
from app.services.pdf_merge_service import merge_pdfs, MergeError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.post("/merge")
async def merge_pdf_endpoint(files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_input", "message": "Upload at least two PDF files to merge."}
        )

    saved_paths: List[Path] = []
    output_path: Path | None = None

    try:
        # Save in the order received — order = merge order, matches PRD 10.2.4
        for upload in files:
            path = save_upload_to_temp(upload)
            saved_paths.append(path)

            try:
                validate_pdf_structure(path)
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail={"error": e.code, "message": e.message}
                )

        try:
            output_path = merge_pdfs(saved_paths)
        except MergeError as e:
            raise HTTPException(
                status_code=422,
                detail={"error": e.code, "message": e.message}
            )

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename="merged.pdf",
            background=None,  # cleanup handled below via cleanup_paths after response scheduling — see note
        )

    except FileNotFoundError:
        # mirrors convert.py's backend_unavailable class for missing-binary style failures
        raise HTTPException(
            status_code=503,
            detail={"error": "backend_unavailable", "message": "Backend processing service unavailable."}
        )
    finally:
        cleanup_paths(saved_paths)
        # Note: output_path cleanup should follow whatever pattern you used in
        # convert.py for post-response deletion (BackgroundTask / cleanup_service),
        # since FileResponse streams after this function returns.