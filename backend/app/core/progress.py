"""Shared cooperative progress and cancellation contracts."""

from collections.abc import Callable

ProgressCallback = Callable[[int, int], None]
StageCallback = Callable[[], None]
CancellationCheck = Callable[[], None]


class JobCancelled(Exception):
    """Raised when an asynchronous conversion job is cancelled."""
