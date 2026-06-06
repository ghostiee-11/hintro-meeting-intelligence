import logging
import sys

import structlog

from app.core.config import settings
from app.core.context import get_trace_id


def _add_trace_id(_logger, _method, event_dict):
    """Structlog processor that injects the current request's trace id."""
    event_dict["traceId"] = get_trace_id()
    return event_dict


def configure_logging() -> None:
    """Structured logging. JSON in production, pretty console in development.

    Every log line carries a timestamp and the request trace id. Request access
    logs (method, path, status, duration) are emitted by the request middleware.
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        _add_trace_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if settings.is_production else logging.DEBUG
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "hintro") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
