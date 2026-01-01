"""
文件工具模块
提供文件路径检查、工具查找等功能
"""

import asyncio
import os
import platform
from pathlib import Path
from typing import Optional


async def check_path_exists(path: str) -> bool:
    """
    检查路径是否存在

    Args:
        path: 文件路径

    Returns:
        路径是否存在
    """
    try:
        return Path(path).exists()
    except (OSError, ValueError):
        return False


async def find_tool_in_system(tool_name: str) -> Optional[str]:
    """
    在系统中查找工具路径

    Args:
        tool_name: 工具名称

    Returns:
        工具路径或None
    """
    system = platform.system().lower()

    if system == "windows":
        # Windows系统使用where命令
        command = ["where", tool_name]
    else:
        # Unix-like系统使用which命令
        command = ["which", tool_name]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # 取所有找到的路径，清理空白字符
            output = stdout.decode().strip()
            paths = [line.strip() for line in output.split("\n") if line.strip()]

            if not paths:
                return None

            # 在 Windows 上，优先选择带 .cmd/.exe/.bat 扩展名的文件
            if system == "windows":
                executable_extensions = [".exe", ".cmd", ".bat"]
                for path in paths:
                    if any(path.lower().endswith(ext) for ext in executable_extensions):
                        return path

                # 如果没找到带扩展名的，返回第一个路径（可能是 Unix 风格脚本）
                return paths[0]
            else:
                # Unix-like 系统直接返回第一个路径
                return paths[0]
        else:
            return None
    except (OSError, asyncio.SubprocessError):
        return None


def is_executable_file(path: str) -> bool:
    """
    检查文件是否为可执行文件

    Args:
        path: 文件路径

    Returns:
        是否为可执行文件
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return False

        # 检查文件扩展名（Windows）
        if platform.system().lower() == "windows":
            executable_extensions = [".exe", ".bat", ".cmd", ".ps1"]
            return path_obj.suffix.lower() in executable_extensions

        # Unix-like系统检查执行权限
        return os.access(path, os.X_OK)
    except (OSError, ValueError):
        return False


def get_file_size(path: str) -> Optional[int]:
    """
    获取文件大小（字节）

    Args:
        path: 文件路径

    Returns:
        文件大小或None
    """
    try:
        return Path(path).stat().st_size
    except (OSError, ValueError):
        return None


def normalize_path(path: str) -> str:
    """
    标准化文件路径

    Args:
        path: 原始路径

    Returns:
        标准化后的路径
    """
    try:
        return str(Path(path).resolve())
    except (OSError, ValueError):
        return path


def ensure_directory_exists(path: str) -> bool:
    """
    确保目录存在，如果不存在则创建

    Args:
        path: 目录路径

    Returns:
        是否成功创建或已存在
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except (OSError, ValueError):
        return False


def get_temp_directory() -> str:
    """
    获取临时目录路径

    Returns:
        临时目录路径
    """
    return os.path.join(os.path.expanduser("~"), "temp")


def is_relative_path(path: str) -> bool:
    """
    检查是否为相对路径

    Args:
        path: 文件路径

    Returns:
        是否为相对路径
    """
    try:
        return not Path(path).is_absolute()
    except (OSError, ValueError):
        return True  # 无法解析时假设为相对路径


def join_paths(*paths: str) -> str:
    """
    连接多个路径

    Args:
        *paths: 路径片段

    Returns:
        连接后的路径
    """
    return str(Path(*paths))


def get_filename(path: str) -> str:
    """
    获取文件名（不包含路径）

    Args:
        path: 文件路径

    Returns:
        文件名
    """
    try:
        return Path(path).name
    except (OSError, ValueError):
        return path


def get_file_extension(path: str) -> str:
    """
    获取文件扩展名

    Args:
        path: 文件路径

    Returns:
        文件扩展名（包含点号）
    """
    try:
        return Path(path).suffix
    except (OSError, ValueError):
        return ""


def remove_extension(path: str) -> str:
    """
    移除文件扩展名

    Args:
        path: 文件路径

    Returns:
        不包含扩展名的文件路径
    """
    try:
        return str(Path(path).with_suffix(""))
    except (OSError, ValueError):
        return path
