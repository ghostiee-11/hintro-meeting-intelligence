from typing import Any


class AppError(Exception):
    """Domain error carrying a stable machine-readable code and HTTP status.

    Rendered by the global exception handler into the unified error envelope.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

    @classmethod
    def not_found(cls, message: str, details: Any | None = None) -> "AppError":
        return cls("NOT_FOUND", message, 404, details)

    @classmethod
    def validation(cls, message: str, details: Any | None = None) -> "AppError":
        return cls("VALIDATION_ERROR", message, 422, details)

    @classmethod
    def unauthorized(cls, message: str = "Authentication required") -> "AppError":
        return cls("UNAUTHORIZED", message, 401)

    @classmethod
    def forbidden(cls, message: str = "You do not have access to this resource") -> "AppError":
        return cls("FORBIDDEN", message, 403)

    @classmethod
    def conflict(cls, message: str, details: Any | None = None) -> "AppError":
        return cls("CONFLICT", message, 409, details)

    @classmethod
    def rate_limited(cls, message: str) -> "AppError":
        return cls("RATE_LIMITED", message, 429)

    @classmethod
    def upstream(cls, message: str, details: Any | None = None) -> "AppError":
        return cls("UPSTREAM_ERROR", message, 502, details)
