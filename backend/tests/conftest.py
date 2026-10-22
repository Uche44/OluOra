import asyncio
import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.core.db import Base, engine as app_engine, get_db

# Use NullPool for testing to prevent open pooled connections from throwing loop-closed errors on teardown
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=pool.NullPool
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
def cleanup_engine():
    yield
    # Dispose engine connections on test session teardown synchronously
    asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
async def reset_app_engine():
    """Drop app.core.db's connection pool after every test.

    Background tasks (email sends) open their own sessions from the application
    engine, which is a real pool rather than this file's NullPool. asyncpg
    connections are bound to the event loop that created them, and pytest-asyncio
    gives each test a fresh loop, so a pooled connection left over from an earlier
    test is unusable and surfaces as "Event loop is closed". A server runs one
    long-lived loop, so this only affects the test harness.
    """
    yield
    await app_engine.dispose()

@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as connection:
        # Start a transaction block
        transaction = await connection.begin()
        # Bind the session to the connection
        async_session = TestingSessionLocal(bind=connection)
        
        yield async_session
        
        # Close the session and roll back the transaction to keep DB clean
        await async_session.close()
        await transaction.rollback()

@pytest.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Override get_db dependency with our test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGI transport for testing the FastAPI application asynchronously
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as async_client:
        yield async_client
        
    app.dependency_overrides.clear()
