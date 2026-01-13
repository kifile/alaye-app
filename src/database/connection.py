"""
Database connection management
"""

import logging
import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configure logger
logger = logging.getLogger(__name__)


def _get_default_db_path() -> str:
    """
    获取系统默认的应用数据目录路径
    统一使用用户主目录下的 .alayeapp 文件夹

    Returns:
        str: 数据库文件的完整路径
    """
    # 统一使用 $HOME/.alayeapp
    db_dir = Path.home() / ".alayeapp"

    # 确保目录存在
    db_dir.mkdir(parents=True, exist_ok=True)

    # 返回数据库文件路径
    db_file = db_dir / "settings.db"
    return f"sqlite+aiosqlite:///{db_file}"


# 数据库配置 - 使用SQLite
DATABASE_URL = _get_default_db_path()

# 创建异步数据库引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 设置为True可以查看SQL语句
    pool_pre_ping=True,  # 连接前验证连接
)

# 创建会话工厂
_SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    Yields:
        AsyncSession: 数据库会话
    """
    async with _SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """
    关闭数据库连接
    """
    logger.info("Closing database connection...")
    await engine.dispose()
    logger.info("Database connection closed")


async def init_db():
    """
    初始化数据库 - 使用 Alembic 迁移
    """
    from alembic import command
    from alembic.config import Config

    # 输出数据库地址
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    logger.info(f"Initializing database at: {db_path}")

    try:
        # Ensure data directory exists (support custom path via environment variable)
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only create if path contains directory
            os.makedirs(db_dir, exist_ok=True)

        # 获取项目根目录和 Alembic 配置文件
        project_root = Path(__file__).parent.parent.parent
        alembic_ini_path = project_root / "alembic.ini"

        # 创建 Alembic 配置
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # 执行迁移到 head
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        raise e
