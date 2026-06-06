import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("redis")


class RedisCache:
    """Thin async Redis wrapper for caching and rate limiting.

    Degrades gracefully: if REDIS_URL is unset or the server is unreachable,
    all operations become no-ops so the application keeps working without Redis.
    """

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None
        if settings.redis_url:
            try:
                self._client = aioredis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("redis_init_failed", error=str(exc))
                self._client = None
        else:
            logger.warning("redis_disabled", reason="REDIS_URL not set")

    async def get_json(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        if not self._client:
            return
        try:
            raw = json.dumps(value, default=str)
            await self._client.set(key, raw, ex=ttl_seconds)
        except Exception:
            pass

    async def delete(self, pattern: str) -> None:
        if not self._client:
            return
        try:
            if "*" in pattern:
                keys = [k async for k in self._client.scan_iter(match=pattern)]
                if keys:
                    await self._client.delete(*keys)
            else:
                await self._client.delete(pattern)
        except Exception:
            pass

    async def incr_window(self, key: str, window_seconds: int) -> int | None:
        """Fixed-window counter. Returns the count, or None if Redis is down."""
        if not self._client:
            return None
        try:
            count = await self._client.incr(key)
            if count == 1:
                await self._client.expire(key, window_seconds)
            return count
        except Exception:
            return None

    async def ping(self) -> bool:
        if not self._client:
            return False
        try:
            return bool(await self._client.ping())
        except Exception:
            return False


cache = RedisCache()
