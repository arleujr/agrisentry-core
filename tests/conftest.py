import sys
import os
import sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection
from sqlalchemy.sql import text
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.selectable import Select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

real_create_async_engine = sqlalchemy.ext.asyncio.create_async_engine


def patched_create_async_engine(url, **kwargs):
    if "sqlite" in str(url):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
    return real_create_async_engine(url, **kwargs)


sqlalchemy.ext.asyncio.create_async_engine = patched_create_async_engine

real_session_execute = AsyncSession.execute


async def patched_session_execute(self, statement, *args, **kwargs):
    if isinstance(statement, str):
        statement = text(statement)
    return await real_session_execute(self, statement, *args, **kwargs)


AsyncSession.execute = patched_session_execute

real_conn_execute = AsyncConnection.execute


async def patched_conn_execute(self, statement, *args, **kwargs):
    if isinstance(statement, str):
        statement = text(statement)
    return await real_conn_execute(self, statement, *args, **kwargs)


AsyncConnection.execute = patched_conn_execute

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"


Select.with_for_update = lambda self, *args, **kwargs: self

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

import core.database

core.database.engine = test_engine
core.database.AsyncSessionLocal = TestSessionLocal

import services.worker

services.worker.engine = test_engine
services.worker.AsyncSessionLocal = TestSessionLocal

from core.database import Base
from models.schemas import Sensor, SensorReading, ActuatorLog


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def init_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        async with test_engine.begin() as conn:
            await conn.execute(SensorReading.__table__.delete())
            await conn.execute(ActuatorLog.__table__.delete())
            await conn.execute(Sensor.__table__.delete())
