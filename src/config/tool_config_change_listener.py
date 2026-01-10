"""
工具配置变更监听器
专门用于监听工具相关配置的变化，并自动检测工具路径和版本信息
"""

import logging
import os
import shutil
from typing import Optional

from ..utils.file_utils import find_tool_in_system
from .config_change_listener import (
    ConfigChangeListener,
    ConfigInitializeEvent,
    ConfigKeyUpdateEvent,
    ConfigListenerResult,
)
from .config_service import config_service

# 配置日志记录器
logger = logging.getLogger(__name__)


class ToolConfigChangeListener(ConfigChangeListener):
    """工具配置变更监听器"""

    def __init__(self):
        self.tool_keys = {
            "npm": ["npm.path", "npm.enable", "npm.version"],
            "claude": ["claude.path", "claude.enable", "claude.version"],
        }

    async def onInitialize(self, event: ConfigInitializeEvent) -> ConfigListenerResult:
        """
        初始化时检测工具状态
        """
        try:
            for tool_name, config_keys in self.tool_keys.items():
                await self._detect_and_update_tool_config(tool_name, config_keys)

            return ConfigListenerResult(success=True, message="工具配置初始化完成")
        except Exception as e:
            return ConfigListenerResult(
                success=False, error_message=f"工具配置初始化失败: {str(e)}"
            )

    async def beforeKeyUpdate(
        self, event: ConfigKeyUpdateEvent
    ) -> ConfigListenerResult:
        """
        配置键更新前的验证
        """
        logger.info(
            f"beforeKeyUpdate - Key: {event.key}, Old value: {event.old_value}, New value: {event.new_value}"
        )
        try:
            key = event.key

            # 如果是工具路径相关配置，验证路径是否有效
            path_keys = [config_keys[0] for config_keys in self.tool_keys.values()]
            if key in path_keys:
                if event.new_value and not shutil.which(event.new_value):
                    return ConfigListenerResult(
                        success=False,
                        error_message=f"指定的工具路径无效: {event.new_value}",
                    )

            return ConfigListenerResult(success=True)

        except Exception as e:
            return ConfigListenerResult(
                success=False, error_message=f"配置验证失败: {str(e)}"
            )

    async def onKeyUpdated(self, event: ConfigKeyUpdateEvent) -> ConfigListenerResult:
        """
        配置键更新后的处理
        """
        logger.info(
            f"onKeyUpdated - Key: {event.key}, New value: {event.new_value}"
        )
        try:
            key = event.key

            # 只有工具路径相关配置更新时，才重新检测该工具的状态
            for tool_name, config_keys in self.tool_keys.items():
                if key == config_keys[0]:  # path key
                    await self._detect_and_update_tool_config(tool_name, config_keys)
                    break

            return ConfigListenerResult(success=True)

        except Exception as e:
            return ConfigListenerResult(
                success=False, error_message=f"配置更新处理失败: {str(e)}"
            )

    async def _detect_and_update_tool_config(self, tool_name: str, config_keys: list):
        """
        检测并更新工具配置
        """
        path_key, enable_key, version_key = config_keys

        # 获取当前工具路径配置
        # 确保数据库已初始化
        try:
            tool_path = await config_service.get_setting(path_key)
        except Exception as e:
            print(f"获取工具路径配置失败: {e}")
            tool_path = None

        if not tool_path:
            # 如果没有配置路径，尝试在系统路径中查找
            tool_path = await find_tool_in_system(tool_name)
            if tool_path:
                await config_service.set_setting(path_key, tool_path)

        if tool_path:
            # 检测工具版本
            version = await self._get_tool_version(tool_name, tool_path)
            enable = bool(version)

            # 更新版本和启用状态
            await config_service.set_setting(version_key, version or "")
            await config_service.set_setting(enable_key, str(enable))
        else:
            # 工具不存在，禁用并清空版本
            await config_service.set_setting(enable_key, "false")
            await config_service.set_setting(version_key, "")

    async def _get_tool_version(self, tool_name: str, tool_path: str) -> Optional[str]:
        """
        获取工具版本信息
        """
        try:
            import platform
            import subprocess

            if tool_name == "npm":
                # 在 Windows 上，npm 是一个批处理文件 npm.cmd
                if platform.system() == "Windows" and not tool_path.endswith(".cmd"):
                    # 尝试找到 npm.cmd
                    npm_cmd_path = tool_path.replace("npm", "npm.cmd")
                    if shutil.which("npm.cmd"):
                        tool_path = "npm.cmd"
                    elif os.path.exists(npm_cmd_path):
                        tool_path = npm_cmd_path
                    else:
                        # 使用系统 PATH 中的 npm
                        tool_path = "npm"

                result = subprocess.run(
                    [tool_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=platform.system() == "Windows",
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    return version

            elif tool_name == "claude":
                # 对于 Claude CLI，可能需要不同的方法
                if platform.system() == "Windows":
                    # 在 Windows 上使用 shell 执行
                    result = subprocess.run(
                        [tool_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True,
                    )
                else:
                    result = subprocess.run(
                        [tool_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return version

            return None

        except Exception:
            return None


# 创建全局工具配置监听器实例
tool_config_listener = ToolConfigChangeListener()
