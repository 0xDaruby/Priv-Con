"""Pydantic response models for PrivCon's local API contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Matches the error contract in setup.md section 6:
    { "error": "<code>", "message": "<human readable message>" }
    """

    error: str
    message: str


class JobStatusResponse(BaseModel):
    """Public snapshot for one in-memory local conversion job."""

    job_id: str
    tool: str
    status: Literal[
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelling",
        "cancelled",
    ]
    stage: Literal[
        "queued",
        "validating",
        "converting",
        "finalizing",
        "ready",
        "cancelling",
        "cancelled",
        "failed",
    ]
    message: str
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    completed_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=1)
    unit_label: str | None = None
    result_available: bool = False
    result_filename: str | None = None
    result_content_type: str | None = None
    error: ErrorResponse | None = None
