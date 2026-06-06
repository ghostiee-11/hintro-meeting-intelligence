import time
from uuid import uuid4

import orjson

from app.core.context import trace_id_var
from app.core.logging import get_logger

logger = get_logger("request")

TRACE_HEADER = b"x-trace-id"

# Paths whose response shape is fixed by contract and must NOT be wrapped.
SKIP_WRAP_EXACT = {
    "/health",
    "/api/evaluation",
    "/openapi.json",
    "/api/openapi.json",
    "/api/integrations/telegram/webhook",
}
SKIP_WRAP_PREFIX = ("/api/docs", "/docs", "/redoc", "/api/redoc")


def _should_wrap(path: str) -> bool:
    if path in SKIP_WRAP_EXACT:
        return False
    return not path.startswith(SKIP_WRAP_PREFIX)


def _set_header(headers: list[tuple[bytes, bytes]], key: bytes, value: bytes) -> list:
    out = [(k, v) for (k, v) in headers if k.lower() != key.lower()]
    out.append((key, value))
    return out


class RequestContextMiddleware:
    """Pure ASGI middleware.

    1. Establishes a trace id (reusing an inbound x-trace-id if present).
    2. Echoes the trace id on the response header.
    3. Wraps successful JSON responses in the unified success envelope, leaving
       streaming (SSE) and contract-fixed endpoints untouched.
    4. Emits a structured access log line per request.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(TRACE_HEADER)
        trace_id = incoming.decode() if incoming else str(uuid4())
        token = trace_id_var.set(trace_id)

        path = scope.get("path", "")
        method = scope.get("method", "")
        wrap = _should_wrap(path)
        start = time.perf_counter()

        state: dict = {"status": 500, "start_msg": None, "ctype": b"", "chunks": []}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                msg_headers = list(message.get("headers") or [])
                state["ctype"] = dict(msg_headers).get(b"content-type", b"")
                state["start_msg"] = {**message, "headers": msg_headers}
                if not self._buffering(wrap, state):
                    message["headers"] = _set_header(msg_headers, TRACE_HEADER, trace_id.encode())
                    await send(message)
                return

            if message["type"] == "http.response.body":
                if not self._buffering(wrap, state):
                    await send(message)
                    return
                state["chunks"].append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                await self._flush_wrapped(send, state, trace_id)
                return

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log = logger.info if state["status"] < 500 else logger.error
            log(
                "request",
                method=method,
                path=path,
                status=state["status"],
                durationMs=duration_ms,
            )
            trace_id_var.reset(token)

    @staticmethod
    def _buffering(wrap: bool, state: dict) -> bool:
        return wrap and state["status"] < 400 and state["ctype"].startswith(b"application/json")

    @staticmethod
    async def _flush_wrapped(send, state: dict, trace_id: str) -> None:
        full = b"".join(state["chunks"])
        try:
            data = orjson.loads(full) if full else None
        except orjson.JSONDecodeError:
            data = None

        if isinstance(data, dict) and "success" in data:
            new_body = full
        else:
            new_body = orjson.dumps({"traceId": trace_id, "success": True, "data": data})

        headers = [
            (k, v) for (k, v) in state["start_msg"]["headers"] if k.lower() != b"content-length"
        ]
        headers = _set_header(headers, TRACE_HEADER, trace_id.encode())
        headers = _set_header(headers, b"content-length", str(len(new_body)).encode())

        await send({"type": "http.response.start", "status": state["status"], "headers": headers})
        await send({"type": "http.response.body", "body": new_body})
