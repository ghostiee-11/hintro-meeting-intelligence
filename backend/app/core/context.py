from contextvars import ContextVar

# Per-request trace id, set by the request-context middleware and read by the
# logger, exception handlers, and response envelope.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    return trace_id_var.get()
