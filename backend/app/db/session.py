import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Under pytest, use NullPool so connections are never shared across the per-test
# event loops (which otherwise raises "Event loop is closed" from asyncpg).
_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if os.getenv("TESTING") == "1":
    _engine_kwargs = {"echo": False, "poolclass": NullPool}

engine = create_async_engine(settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
