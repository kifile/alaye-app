"""
进程执行工具模块
提供异步进程执行和结果返回的统一接口
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

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
