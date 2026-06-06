import os

os.environ["TESTING"] = "1"  # must be set before app/engine import
os.environ["REDIS_URL"] = ""  # disable Redis so rate limiting fails open in tests

import uuid  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@test.com"
