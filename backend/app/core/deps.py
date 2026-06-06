from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import cache
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError.unauthorized("Missing authentication token")
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError.unauthorized("Invalid token payload")
    user = await db.get(User, user_id)
    if user is None:
        raise AppError.unauthorized("User no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_cron(x_cron_secret: Annotated[str | None, Header()] = None) -> None:
    """Protects the scheduled-job trigger endpoint with the shared cron secret."""
    if not x_cron_secret or x_cron_secret != settings.cron_secret:
        raise AppError.unauthorized("Invalid or missing cron secret")


def rate_limit(limit: int, window_seconds: int):
    """Dependency factory: fixed-window rate limit keyed by client IP and route.

    Fails open when Redis is unavailable so the API stays usable without Redis.
    """

    async def _dep(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        route = request.url.path
        key = f"ratelimit:{route}:{client}"
        count = await cache.incr_window(key, window_seconds)
        if count is not None and count > limit:
            raise AppError.rate_limited(
                f"Too many requests. Limit is {limit} per {window_seconds}s."
            )

    return _dep


# Re-export for routers that need a raw select on User.
__all__ = ["DbSession", "CurrentUser", "get_current_user", "require_cron", "rate_limit", "select"]
