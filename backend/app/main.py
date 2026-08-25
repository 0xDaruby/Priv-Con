"""FastAPI application entrypoint."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.logging_config import configure_logging
from app.core.security import (
    ProcessingConcurrencyMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
    UploadOriginMiddleware,
)
from app.models.schemas import ErrorResponse
from app.routers import convert, health, images, pdf
from app.services.cleanup_service import cleanup_lifespan

configure_logging()

app = FastAPI(title="PrivCon API", lifespan=cleanup_lifespan)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request,
    __: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="invalid_input",
            message="The request contains missing or invalid fields.",
        ).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    _: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    known_error_code = {
        404: "not_found",
        405: "method_not_allowed",
    }.get(exc.status_code)
    known_message = {
        404: "The requested API endpoint was not found.",
        405: "This HTTP method is not supported for the requested endpoint.",
    }.get(exc.status_code)

    if known_error_code is not None and known_message is not None:
        error_code = known_error_code
        message = known_message
    elif 400 <= exc.status_code < 500:
        error_code = "invalid_input"
        message = "The request could not be processed."
    else:
        error_code = "internal_error"
        message = "An unexpected server error occurred."

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=error_code,
            message=message,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected server error occurred.",
        ).model_dump(),
    )


# Middleware is registered inside-out. SecurityHeaders is last so it also
# covers CORS preflights and request-limit/origin rejection responses.
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(ProcessingConcurrencyMiddleware)
app.add_middleware(UploadOriginMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health.router)
app.include_router(convert.router)
app.include_router(pdf.router)
app.include_router(images.router)
