"""Test fixtures.

Uses TEST_DATABASE_URL if set (e.g. against the docker-compose postgres), otherwise
skips DB-backed tests. Alembic-migrates + seeds once per session.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from app.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.user import User  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_db():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    await seed()
    yield


@pytest_asyncio.fixture()
async def db():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture()
async def auth_headers(client, db: AsyncSession):
    # dev-login upserts + returns HS256 JWT
    unique = uuid.uuid4().hex[:8]
    payload = {"email": f"u_{unique}@test.local", "auth_provider_id": f"clerk_{unique}"}
    resp = await client.post("/api/v1/auth/dev-login", json=payload)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
