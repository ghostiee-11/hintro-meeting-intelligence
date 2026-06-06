from typing import Any

from app.core.context import get_trace_id


def success_envelope(data: Any) -> dict[str, Any]:
    return {"traceId": get_trace_id(), "success": True, "data": data}


def error_envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"traceId": get_trace_id(), "success": False, "error": error}
