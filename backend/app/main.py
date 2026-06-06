from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.envelope import error_envelope
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware

configure_logging()
logger = get_logger("app")

app = FastAPI(
    title=settings.app_name,
    description=(
        "Grounded AI meeting insights, action item tracking, overdue detection, and reminders. "
        "All business endpoints return the unified envelope { traceId, success, data | error }."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Order matters: CORS is outermost, then our request-context/envelope middleware.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-trace-id"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(p) for p in err.get("loc", [])), "message": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_envelope("VALIDATION_ERROR", "Request validation failed", details),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        429: "RATE_LIMITED",
    }.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(code, str(exc.detail)),
    )


@app.exception_handler(Exception)
async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
    )


app.include_router(api_router)
