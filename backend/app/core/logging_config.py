"""Privacy-safe logging configuration for conversion job lifecycle events."""

import logging
from typing import Literal

JobStatus = Literal["started", "success", "failure"]


class _PrivConLogHandler(logging.StreamHandler):
    """Marker type used to avoid installing duplicate handlers."""


def configure_logging() -> None:
    """Configure timestamps and enable PrivCon informational job events."""
    privcon_logger = logging.getLogger("privcon")
    privcon_logger.setLevel(logging.INFO)
    privcon_logger.propagate = False

    if not any(
        isinstance(handler, _PrivConLogHandler) for handler in privcon_logger.handlers
    ):
        handler = _PrivConLogHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        privcon_logger.addHandler(handler)


def log_job_event(
    logger: logging.Logger,
    *,
    tool: str,
    job_id: str,
    status: JobStatus,
) -> None:
    """Log only controlled, non-user-supplied conversion metadata."""
    logger.info(
        "tool=%s job_id=%s status=%s",
        tool,
        job_id,
        status,
    )
