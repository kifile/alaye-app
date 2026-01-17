"""
Test configuration and fixtures
"""

import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Store test database path
_TEST_DB_PATH = None


def get_test_db_path():
    """Get the path to the test database"""
    global _TEST_DB_PATH
    if _TEST_DB_PATH is None:
        # Create a temporary database for testing
        temp_dir = tempfile.mkdtemp(prefix="alaye_test_")
        db_file = Path(temp_dir) / "test.db"
        _TEST_DB_PATH = f"sqlite+aiosqlite:///{db_file}"
    return _TEST_DB_PATH


def get_test_db_file():
    """Get the test database file path (for cleanup)"""
    return get_test_db_path().replace("sqlite+aiosqlite:///", "")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine and create all tables"""
    db_path = get_test_db_path()

    engine = create_async_engine(
        db_path,
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables using SQLAlchemy
    from src.database.orms.base import Base

    print(f"Creating database tables for: {db_path}")

    async with engine.begin() as conn:
        await conn.run_sync(lambda connection: Base.metadata.create_all(connection))

    print("Database tables created successfully")

    yield engine

    # Cleanup
    await engine.dispose()

    # Delete test database file
    try:
        db_file = get_test_db_file()
        if Path(db_file).exists():
            Path(db_file).unlink()
            # Also remove parent directory if empty
            parent_dir = Path(db_file).parent
            if parent_dir.exists() and parent_dir.is_dir():
                import shutil

                shutil.rmtree(parent_dir, ignore_errors=True)
    except Exception as e:
        print(f"Warning: Failed to cleanup test database: {e}")


@pytest.fixture(scope="function")
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with proper data isolation"""
    from src.database.orms.ai_project import AIProject
    from src.database.orms.ai_project_session import AIProjectSession
    from src.database.orms.app_setting import AppSetting

    _SessionLocal = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with _SessionLocal() as session:
        yield session

    # Delete all data from tables after each test
    async with _SessionLocal() as cleanup_session:
        await cleanup_session.run_sync(
            lambda session: session.query(AIProjectSession).delete()
        )
        await cleanup_session.run_sync(
            lambda session: session.query(AIProject).delete()
        )
        await cleanup_session.run_sync(
            lambda session: session.query(AppSetting).delete()
        )
        await cleanup_session.commit()


@pytest.fixture(scope="function")
async def mock_get_db(test_db_session: AsyncSession):
    """
    Mock get_db() to return test database session.

    This fixture patches both project_service and config_service to use the test database.
    The test_db_session is automatically rolled back after each test.
    """
    from unittest.mock import patch

    @asynccontextmanager
    async def _mock_get_db():
        yield test_db_session

    # Apply patches as context managers
    with patch("src.project.project_service.get_db", side_effect=_mock_get_db):
        with patch("src.config.config_service.get_db", side_effect=_mock_get_db):
            yield test_db_session
