"""Shared exception types for the conversion pipeline."""


class PrivConError(Exception):
    """Base exception carrying a machine-readable code and a user-facing message.

    The (code, message) pair maps directly onto the API contract's error
    shape defined in setup.md section 6:
        { "error": "<code>", "message": "<message>" }
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationError(PrivConError):
    """Raised when an uploaded file fails extension or structural validation."""


class ConversionError(PrivConError):
    """Raised when the LibreOffice conversion subprocess fails, times out,
    or the input file is missing."""


class JobCapacityError(PrivConError):
    """Raised when the local asynchronous job capacity is exhausted."""


class JobLookupError(PrivConError):
    """Raised when a job or its result cannot be retrieved."""
