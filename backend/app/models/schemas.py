"""Pydantic response models.

Kept intentionally small for Phase 1 step 4 — extended as the merge/split/
images endpoints land in later steps.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Matches the error contract in setup.md section 6:
    { "error": "<code>", "message": "<human readable message>" }
    """

    error: str
    message: str
