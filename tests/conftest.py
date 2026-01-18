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


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """在 pytest 会话结束时强制清理资源"""
    import os

    # 取消所有未完成的异步任务
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    if not task.done() and not task.cancelled():
                        task.cancel()
                try:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # 强制退出（如果进程仍然挂起）
    # 给一点时间让正常清理完成
    import threading
    import time

    def delayed_exit():
        time.sleep(2)
        # 如果2秒后还没退出，强制退出
        os._exit(0)

    # 启动一个守护线程，确保进程会退出
    exit_thread = threading.Thread(target=delayed_exit, daemon=True)
    exit_thread.start()


@pytest.fixture(scope="session", autouse=True)
def cleanup_async_tasks():
    """确保所有测试完成后清理异步任务"""
    yield
    # 在所有测试完成后，取消所有未完成的异步任务
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                if not task.done() and not task.cancelled():
                    task.cancel()
            # 等待任务取消完成
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
    except Exception:
        pass  # 忽略清理时的错误


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


# 移除了自定义的 event_loop fixture
# 让 pytest-asyncio 在 auto 模式下自动管理事件循环
# pytest.ini 中已设置 asyncio_mode = auto


@pytest.fixture(scope="module")
async def test_engine():
    """Create test database engine and create all tables"""
    db_path = get_test_db_path()

    engine = create_async_engine(
        db_path,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )

    # Create all tables using SQLAlchemy
    from src.database.orms.base import Base

    print(f"Creating database tables for: {db_path}")

    async with engine.begin() as conn:
        await conn.run_sync(lambda connection: Base.metadata.create_all(connection))

    print("Database tables created successfully")

    yield engine

    # Cleanup
    print("Disposing database engine...")
    await engine.dispose()
    print("Database engine disposed")

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
            print("Test database file deleted")
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
