"""
数据库连接管理
"""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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
DATABASE_URL = os.getenv("DATABASE_URL", _get_default_db_path())

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


async def init_db():
    """
    初始化数据库 - 创建所有表
    """
    from .orms.base import Base

    # 输出数据库地址
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    print(f"[Database] Initializing database at: {db_path}")
    print(f"[Database] Database file exists: {Path(db_path).exists()}")

    # 检查环境变量
    if "DATABASE_URL" in os.environ:
        print(f"[Database] Using DATABASE_URL from environment variable")

    # 确保数据目录存在（支持通过环境变量自定义路径的情况）
    db_dir = os.path.dirname(db_path)
    if db_dir:  # 只有在路径中包含目录时才创建
        os.makedirs(db_dir, exist_ok=True)
        print(f"[Database] Directory exists: {Path(db_dir).exists()}")

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 再次检查文件是否被创建
    print(f"[Database] Database file exists after init: {Path(db_path).exists()}")
    print("[Database] Database initialized successfully")


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
