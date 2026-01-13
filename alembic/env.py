import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 添加项目根目录到sys.path，以便导入src模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 动态设置数据库 URL，与 connection.py 保持一致
db_dir = Path.home() / ".alayeapp"
db_file = db_dir / "settings.db"

# 确保数据库目录存在
db_dir.mkdir(parents=True, exist_ok=True)

database_url = f"sqlite+aiosqlite:///{db_file}"
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

from src.database.orms.ai_project import AIProject
from src.database.orms.ai_project_session import AIProjectSession

# 导入所有模型以确保它们被注册到Base.metadata
from src.database.orms.app_setting import AppSetting

# add your model's MetaData object here
# for 'autogenerate' support
from src.database.orms.base import Base

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    try:
        # 检查是否已有运行中的事件循环
        loop = asyncio.get_running_loop()
        # 如果有事件循环在运行，说明我们在异步上下文中
        # 需要在新线程中运行，因为 asyncio.run() 不能在已有循环中创建新循环
        import threading

        result = [None]
        exception = [None]

        def run_in_thread():
            try:
                asyncio.run(run_async_migrations())
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()

        if exception[0]:
            raise exception[0]
    except RuntimeError:
        # 没有运行中的事件循环，可以安全使用 asyncio.run
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
