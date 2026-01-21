"""
Database connection management
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configure logger
logger = logging.getLogger(__name__)


def _get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径，支持 Nuitka 打包后的环境

    Args:
        relative_path: 相对于项目根目录的相对路径

    Returns:
        Path: 资源文件的绝对路径
    """
    import sys

    # 尝试多个可能的路径来源
    candidates = []

    # 检测是否在 Nuitka 环境
    is_nuitka = "__nuitka__" in globals() or "__compiled__" in globals()

    # 1. 尝试从当前可执行文件目录推导（Nuitka 打包环境）
    if is_nuitka and "__file__" in globals():
        try:
            # 在 Nuitka 环境中，__file__ 指向编译后的 .pyc 文件位置
            # 资源文件通常在同一目录或父目录
            current_dir = Path(__file__).parent
            candidates.append(current_dir / relative_path)
            logger.debug(
                f"Nuitka: Added path from __file__ parent: {current_dir / relative_path}"
            )
        except Exception as e:
            logger.debug(f"Could not get path from Nuitka __file__: {e}")

    # 2. 尝试从 Nuitka 二进制目录推导
    try:
        nuitka_dir = globals().get("__nuitka_binary_dir")
        if nuitka_dir:
            nuitka_root = Path(nuitka_dir)
            candidates.append(nuitka_root / relative_path)
            logger.debug(
                f"Nuitka: Added path from __nuitka_binary_dir: {nuitka_root / relative_path}"
            )
    except Exception as e:
        logger.debug(f"Could not get Nuitka binary dir: {e}")

    # 3. 尝试从 __file__ 推导（正常 Python 环境）
    try:
        if "__file__" in globals():
            project_root = Path(__file__).parent.parent.parent
            candidates.append(project_root / relative_path)
            logger.debug(
                f"Added path from __file__ project root: {project_root / relative_path}"
            )
    except Exception as e:
        logger.debug(f"Could not get path from __file__: {e}")

    # 4. 尝试从当前工作目录推导
    try:
        candidates.append(Path.cwd() / relative_path)
        logger.debug(f"Added path from cwd: {Path.cwd() / relative_path}")
    except Exception as e:
        logger.debug(f"Could not get path from cwd: {e}")

    # 5. 尝试从 sys.argv[0] 推导
    try:
        if sys.argv and sys.argv[0]:
            argv0_path = Path(sys.argv[0]).parent
            candidates.append(argv0_path / relative_path)
            logger.debug(f"Added path from sys.argv[0]: {argv0_path / relative_path}")
    except Exception as e:
        logger.debug(f"Could not get path from sys.argv[0]: {e}")

    # 返回第一个存在的路径
    for candidate in candidates:
        logger.debug(f"Checking path candidate: {candidate}")
        try:
            if candidate.exists():
                logger.info(f"Found resource at: {candidate}")
                return candidate
        except Exception as e:
            logger.debug(f"Error checking path {candidate}: {e}")

    # 如果都不存在，返回第一个候选（通常是最可能的位置）
    default_path = candidates[0] if candidates else Path(relative_path)
    logger.warning(f"Resource not found, returning first candidate: {default_path}")
    return default_path


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


@asynccontextmanager
async def get_db():
    """
    获取数据库会话的异步上下文管理器

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


async def _init_db_internal():
    """
    内部数据库初始化函数 - 执行实际的 Alembic 迁移工作。

    此函数包含所有 Alembic 迁移逻辑，应在独立子进程中调用
    以避免日志配置问题。
    """
    import tempfile
    import zipfile

    from alembic import command
    from alembic.config import Config

    # 输出数据库地址
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    logger.info(f"Initializing database at: {db_path}")

    # ========== 诊断日志：路径信息 ==========
    logger.info("=" * 70)
    logger.info("ALEMBIC DIAGNOSIS - Path Information")
    logger.info("=" * 70)

    # 记录当前文件路径
    logger.info(f"__file__ = {__file__}")

    # 检查是否在 Nuitka 环境中运行
    nuitka_dir = globals().get("__nuitka_binary_dir")
    is_nuitka = "__nuitka__" in globals() or "__compiled__" in globals()

    if nuitka_dir:
        logger.info(f"Running in Nuitka environment")
        logger.info(f"__nuitka_binary_dir = {nuitka_dir}")
    elif is_nuitka:
        logger.info(
            f"Running in Nuitka environment (detected via __nuitka__ or __compiled__)"
        )
        # 尝试获取二进制目录
        try:
            import sys

            if hasattr(sys, "_MEIPASS"):  # PyInstaller
                nuitka_dir = sys._MEIPASS
            elif "__file__" in globals():
                # Nuitka: 可执行文件所在目录
                nuitka_dir = str(Path(__file__).parent)
            logger.info(f"Detected binary directory: {nuitka_dir}")
        except Exception as e:
            logger.warning(f"Could not determine binary directory: {e}")
    else:
        logger.info("Running in normal Python environment (not Nuitka)")

    # 使用辅助函数获取资源路径
    logger.info("\nUsing _get_resource_path helper to locate files...")
    alembic_ini_path = _get_resource_path("alembic.ini")

    # 检查是否需要从 zip 解压 alembic_migrations
    alembic_zip_path = _get_resource_path("alembic_migrations.zip")
    alembic_dir = None
    temp_dir = None

    if alembic_zip_path.exists():
        logger.info(f"Found alembic_migrations.zip at: {alembic_zip_path}")
        logger.info("Extracting alembic_migrations.zip to temporary directory...")

        # 创建临时目录并解压
        temp_dir = Path(tempfile.mkdtemp(prefix="alembic_migrations_"))
        logger.info(f"Created temporary directory: {temp_dir}")

        try:
            with zipfile.ZipFile(alembic_zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
                logger.info(f"Extracted {len(zip_ref.namelist())} files")

            alembic_dir = temp_dir / "alembic_migrations"
            logger.info(f"Extracted alembic_migrations directory: {alembic_dir}")

            if not alembic_dir.exists():
                raise FileNotFoundError(
                    f"Expected alembic_migrations directory not found in zip"
                )

        except Exception as e:
            logger.error(f"Failed to extract alembic_migrations.zip: {e}")
            if temp_dir:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    else:
        logger.info(
            "alembic_migrations.zip not found, looking for alembic_migrations directory..."
        )
        alembic_dir = _get_resource_path("alembic_migrations")

    logger.info("\nDetailed path information:")
    logger.info(f"  alembic.ini path = {alembic_ini_path}")
    logger.info(f"  alembic.ini exists = {alembic_ini_path.exists()}")
    logger.info(f"  alembic_migrations/ path = {alembic_dir}")
    logger.info(f"  alembic_migrations/ exists = {alembic_dir.exists()}")

    if alembic_dir and alembic_dir.exists():
        # 检查 versions 目录
        alembic_versions_dir = alembic_dir / "versions"
        logger.info(f"  alembic_migrations/versions path = {alembic_versions_dir}")
        logger.info(
            f"  alembic_migrations/versions exists = {alembic_versions_dir.exists()}"
        )

        # 列出 alembic_migrations 目录下的文件
        try:
            files_in_alembic = list(alembic_dir.iterdir())
            logger.info(
                f"  Files in alembic_migrations/: {[f.name for f in files_in_alembic]}"
            )
        except Exception as e:
            logger.warning(f"  Could not list alembic_migrations/ directory: {e}")

    logger.info("=" * 70)

    try:
        # Ensure data directory exists (support custom path via environment variable)
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only create if path contains directory
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

        # 创建 Alembic 配置
        logger.info(f"Creating Alembic config from: {alembic_ini_path}")

        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at: {alembic_ini_path}")

        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # 关键：设置 script_location 指向 alembic_migrations 目录
        if not alembic_dir.exists():
            raise FileNotFoundError(
                f"alembic_migrations directory not found at: {alembic_dir}"
            )

        alembic_cfg.set_main_option("script_location", str(alembic_dir))
        logger.info(f"Set script_location to: {alembic_dir}")

        # 记录当前配置
        logger.info("Alembic configuration:")
        logger.info(
            f"  sqlalchemy.url = {alembic_cfg.get_main_option('sqlalchemy.url')}"
        )
        logger.info(
            f"  script_location = {alembic_cfg.get_main_option('script_location')}"
        )

        # 执行迁移到 head
        logger.info("Starting Alembic upgrade to head...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")

        # 清理临时目录（如果是从 zip 解压的）
        if temp_dir:
            import shutil

            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        logger.error(f"Database migration failed with error: {e}", exc_info=True)

        # 清理临时目录（即使在失败时）
        if temp_dir:
            import shutil

            logger.info(f"Cleaning up temporary directory after error: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

        raise e


async def init_db():
    """
    初始化数据库 - 使用 Alembic 迁移

    此函数会在独立子进程中执行数据库初始化，避免 Alembic 的日志配置
    影响主进程。

    Raises:
        RuntimeError: 如果子进程执行失败，异常信息会包含详细的错误原因
    """
    from src.utils.process_utils import run_in_subprocess

    # run_in_subprocess 会在失败时抛出 RuntimeError 并包含详细错误信息
    await run_in_subprocess(_init_db_internal, "database initialization")
