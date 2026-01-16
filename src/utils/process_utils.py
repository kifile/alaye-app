"""
进程执行工具模块
提供异步进程执行和结果返回的统一接口
"""

import asyncio
import logging
import multiprocessing
import subprocess
import sys
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProcessResult(BaseModel):
    """进程执行结果"""

    success: bool = Field(description="是否执行成功")
    return_code: int = Field(description="进程返回码")
    stdout: str = Field(default="", description="标准输出")
    stderr: str = Field(default="", description="标准错误输出")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    @classmethod
    def create_success(
        cls, return_code: int, stdout: str, stderr: str = ""
    ) -> "ProcessResult":
        """创建成功结果"""
        return cls(
            success=True,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
        )

    @classmethod
    def create_failure(
        cls, return_code: int, error_message: str, stdout: str = "", stderr: str = ""
    ) -> "ProcessResult":
        """创建失败结果"""
        return cls(
            success=False,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            error_message=error_message,
        )


def run_process(
    command: List[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    cwd: Optional[Path] = None,
) -> ProcessResult:
    """
    执行进程并返回结果

    Args:
        command: 命令列表，如 ["claude", "plugin", "install", "plugin@marketplace"]
        capture_output: 是否捕获输出，默认为 True
        text: 是否以文本模式返回输出，默认为 True
        check: 是否在返回非零状态码时抛出异常，默认为 False
        cwd: 工作目录，默认为 None（当前目录）

    Returns:
        ProcessResult: 进程执行结果，包含成功状态、输出和错误信息

    Example:
        result = run_process(["claude", "plugin", "install", "code-review@anthropics"])
        if result.success:
            logger.info(f"安装成功: {result.stdout}")
        else:
            logger.error(f"安装失败: {result.error_message}")
    """
    try:
        logger.info(f"执行命令: {' '.join(command)}")
        if cwd:
            logger.info(f"工作目录: {cwd}")

        # 准备 subprocess 参数
        subprocess_kwargs = {
            "capture_output": capture_output,
            "text": text,
            "check": check,
            "encoding": "utf-8",
            "errors": "replace",
            "cwd": cwd,
        }

        # 在 Windows 上防止弹出终端窗口
        if sys.platform == "win32":
            subprocess_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command, **subprocess_kwargs)

        if result.returncode == 0:
            logger.info(f"命令执行成功，返回码: {result.returncode}")
            return ProcessResult.create_success(
                return_code=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
        else:
            error_msg = f"命令执行失败，返回码: {result.returncode}"
            if result.stderr:
                error_msg += f", 错误: {result.stderr}"
            logger.error(error_msg)
            return ProcessResult.create_failure(
                return_code=result.returncode,
                error_message=error_msg,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

    except FileNotFoundError:
        error_msg = f"未找到命令: {command[0]}"
        logger.error(error_msg)
        return ProcessResult.create_failure(
            return_code=-1,
            error_message=error_msg,
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行异常: {e}"
        if e.stderr:
            error_msg += f", 错误: {e.stderr}"
        logger.error(error_msg)
        return ProcessResult.create_failure(
            return_code=e.returncode,
            error_message=error_msg,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
        )
    except Exception as e:
        error_msg = f"执行命令时发生未知错误: {e}"
        logger.error(error_msg)
        return ProcessResult.create_failure(
            return_code=-1,
            error_message=error_msg,
        )


def _subprocess_entry(
    func_queue: multiprocessing.Queue, exception_queue: multiprocessing.Queue
) -> None:
    """
    子进程入口函数（模块级别，可被 multiprocessing 序列化）。

    此函数在子进程中执行，从队列中获取异步函数并运行，处理异常。

    Args:
        func_queue: 用于接收异步函数和函数名的队列
        exception_queue: 用于传递异常信息的队列
    """
    # 从队列中获取函数和函数名
    func_data: tuple[Callable[[], Awaitable[None]], str] = func_queue.get()
    async_func, func_name = func_data

    if async_func is None:
        error_msg = "No async function set for subprocess"
        logger.error(error_msg)
        exception_queue.put((None, error_msg, None))
        sys.exit(1)

    try:
        asyncio.run(async_func())
        sys.exit(0)
    except Exception as e:
        import traceback

        name = func_name or "unknown"
        error_msg = f"{name} failed in subprocess: {e}"
        logger.error(error_msg, exc_info=True)
        # 将异常信息放入队列，传递给父进程
        exception_queue.put((type(e).__name__, str(e), traceback.format_exc()))
        sys.exit(1)


async def run_in_subprocess(
    async_func: Callable[[], Awaitable[None]], func_name: str = "async_function"
) -> bool:
    """
    在独立子进程中执行异步函数，避免子进程的日志/配置影响主进程。

    使用 multiprocessing 模块创建子进程：
    - Unix/Linux/macOS: 使用 fork()（高效，复制父进程内存）
    - Windows: 使用 spawn()（启动新的 Python 解释器）

    线程安全：使用队列传递函数，支持并发调用。

    Args:
        async_func: 要执行的异步函数（必须是模块级函数以便 pickle，不支持闭包/局部函数）
        func_name: 函数名称，用于日志输出

    Returns:
        bool: 执行是否成功

    Raises:
        RuntimeError: 如果子进程执行失败，异常信息会包含原始错误详情

    Example:
        from src.utils.process_utils import run_in_subprocess

        async def my_init_task():
            # ... some async work
            pass

        try:
            success = await run_in_subprocess(my_init_task, "my_init_task")
        except RuntimeError as e:
            logger.error(f"Task failed: {e}")
    """
    logger.info(f"Running {func_name} in subprocess...")

    # 创建队列，用于父进程和子进程之间传递数据
    func_queue = multiprocessing.Queue()
    exception_queue = multiprocessing.Queue()

    try:
        # 将函数和函数名放入队列，子进程会从这里读取
        func_queue.put((async_func, func_name))

        # Unix 系统使用 fork（子进程继承父进程内存，不需要 pickle）
        # Windows 使用 spawn（需要 pickle 函数，所以 async_func 必须是可序列化的）
        if sys.platform != "win32":
            ctx = multiprocessing.get_context("fork")
        else:
            ctx = multiprocessing.get_context("spawn")

        # 创建进程，传递函数队列和异常队列
        process = ctx.Process(
            target=_subprocess_entry, args=(func_queue, exception_queue)
        )

        # 启动子进程
        process.start()
        logger.info(f"Subprocess started for {func_name} (PID: {process.pid})")

        # 等待子进程完成
        process.join()

        # 检查退出码
        if process.exitcode == 0:
            logger.info(f"Subprocess for {func_name} completed successfully")
            return True
        else:
            # 从队列中获取异常信息
            error_details = []
            while not exception_queue.empty():
                exc_type, exc_msg, exc_tb = exception_queue.get()
                if exc_type:
                    error_details.append(f"{exc_type}: {exc_msg}")
                else:
                    error_details.append(exc_msg)

            error_msg = (
                f"Subprocess for {func_name} failed with exit code: {process.exitcode}"
            )
            if error_details:
                error_msg += f" | Details: {'; '.join(error_details)}"

            logger.error(error_msg)
            raise RuntimeError(error_msg)

    finally:
        # 清理队列资源，防止资源泄漏
        func_queue.close()
        exception_queue.close()
        func_queue.join_thread()
        exception_queue.join_thread()
