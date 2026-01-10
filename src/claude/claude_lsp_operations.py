"""
LSP 配置操作模块
处理 LSP 服务器的扫描等操作
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .models import ConfigScope, LSPServerInfo

if TYPE_CHECKING:
    from .claude_plugin_operations import ClaudePluginOperations

# Configure logger
logger = logging.getLogger("claude")


class ClaudeLSPOperations:
    """Claude LSP 操作类"""

    def __init__(
        self,
        project_path: Path,
        user_home: Path | None = None,
        plugin_ops: Optional["ClaudePluginOperations"] = None,
    ):
        """
        初始化 LSP 操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
            plugin_ops: 可选的插件操作实例，用于扫描插件提供的 LSP 服务器
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()
        self.plugin_ops = plugin_ops

    async def scan_lsp(self, scope: ConfigScope | None = None) -> List[LSPServerInfo]:
        """
        扫描并获取所有 LSP 配置

        扫描已安装插件提供的 LSP 服务器。

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 LSP 服务器。
                   None 表示返回所有作用域的服务器。
                   目前仅支持 plugin 作用域。

        Returns:
            List[LSPServerInfo]: LSP 服务器配置信息列表
        """
        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 LSP 服务器
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 获取已安装的插件列表
                plugins = await self.plugin_ops.scan_plugins()

                # 筛选出已启用的插件
                enabled_plugins = [
                    p for p in plugins if p.installed and p.enabled and p.tools
                ]

                # 从已启用插件中提取 LSP 服务器
                all_lsp_servers = []
                for plugin in enabled_plugins:
                    if plugin.tools and plugin.tools.lsp_servers:
                        all_lsp_servers.extend(plugin.tools.lsp_servers)

                return all_lsp_servers
            except Exception as e:
                logger.error(f"Failed to scan plugin LSP servers: {e}")

        return []
