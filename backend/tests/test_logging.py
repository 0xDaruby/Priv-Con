"""Tests for privacy-safe conversion job logging."""

import logging
import re
from io import StringIO

from app.core.logging_config import configure_logging, log_job_event


def test_job_logging_has_timestamp_and_only_controlled_metadata() -> None:
    configure_logging()
    logger = logging.getLogger("privcon.jobs")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)

    try:
        log_job_event(
            logger,
            tool="images-to-pdf",
            job_id="internal-job-id",
            status="failure",
        )
    finally:
        logger.removeHandler(handler)

    log_line = stream.getvalue().strip()
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ", log_line)
    assert log_line.endswith(
        "INFO privcon.jobs "
        "tool=images-to-pdf job_id=internal-job-id status=failure"
    )
    assert "filename" not in log_line.lower()
    assert "content" not in log_line.lower()
