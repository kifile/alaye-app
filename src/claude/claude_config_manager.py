"""
Claude 配置管理器
扫描、加载和管理项目中的 Claude Code 配置文件和配置信息
"""

from pathlib import Path
from typing import List, Optional

from ..utils.process_utils import ProcessResult
from .claude_hooks_operations import ClaudeHooksOperations
from .claude_lsp_operations import ClaudeLSPOperations
from .claude_markdown_operations import ClaudeMarkdownOperations
from .claude_mcp_operations import ClaudeMCPOperations
from .claude_plugin_operations import ClaudePluginOperations
from .claude_settings_operations import ClaudeSettingsOperations
from .models import (
    ClaudeMemoryInfo,
    ClaudeSettingsInfoDTO,
    ConfigScope,
    HookConfig,
    HookEvent,
    HooksInfo,
    LSPServerInfo,
    MarkdownContentDTO,
    MCPInfo,
    MCPServer,
    PluginInfo,
    PluginMarketplaceInfo,
)


class ClaudeConfigManager:
    """Claude 配置管理器"""

    def __init__(self, project_path: str, user_home: str | None = None):
        """
        初始化配置管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
        """
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise ValueError(f"项目路径不存在: {project_path}")

        # 设置用户主目录路径
        self.user_home = Path(user_home).resolve() if user_home else Path.home()

        # 初始化插件操作模块（其他操作模块依赖它）
        self.plugin_ops = ClaudePluginOperations(self.project_path, self.user_home)

        # 初始化各个操作模块，传入 plugin_ops 以支持插件资源扫描
        self.markdown_ops = ClaudeMarkdownOperations(
            self.project_path, self.user_home, self.plugin_ops
        )
        self.hooks_ops = ClaudeHooksOperations(
            self.project_path, self.user_home, self.plugin_ops
        )
        self.mcp_ops = ClaudeMCPOperations(
            self.project_path, self.user_home, self.plugin_ops
        )
        self.lsp_ops = ClaudeLSPOperations(
            self.project_path, self.user_home, self.plugin_ops
        )
        self.settings_ops = ClaudeSettingsOperations(self.project_path, self.user_home)

    # MCP 相关操作
    async def scan_mcp_servers(self, scope: ConfigScope | None = None) -> MCPInfo:
        """
        扫描 MCP 服务器配置

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 MCP 服务器。
                   None 表示返回所有作用域的服务器。

        Returns:
            MCPInfo: MCP 配置信息
        """
        return await self.mcp_ops.scan_mcp(scope)

    def remove_mcp_server(
        self, name: str, scope: ConfigScope = ConfigScope.project
    ) -> bool:
        """删除 MCP 服务器"""
        return self.mcp_ops.remove_mcp_server(name, scope)

    def add_mcp_server(
        self, name: str, server: MCPServer, scope: ConfigScope = ConfigScope.project
    ) -> None:
        """添加 MCP 服务器"""
        return self.mcp_ops.add_mcp_server(name, server, scope)

    def update_mcp_server(
        self, name: str, server: MCPServer, scope: ConfigScope = ConfigScope.project
    ) -> bool:
        """更新 MCP 服务器配置"""
        return self.mcp_ops.update_mcp_server(name, server, scope)

    def rename_mcp_server(
        self,
        old_name: str,
        new_name: str,
        old_scope: ConfigScope = ConfigScope.project,
        new_scope: ConfigScope = None,
    ) -> bool:
        """重命名 MCP 服务器或更改其作用域"""
        return self.mcp_ops.rename_mcp_server(old_name, new_name, old_scope, new_scope)

    def enable_mcp_server(self, name: str) -> None:
        """启用 MCP 服务器"""
        return self.mcp_ops.enable_mcp_server(name)

    def disable_mcp_server(self, name: str) -> None:
        """禁用 MCP 服务器"""
        return self.mcp_ops.disable_mcp_server(name)

    def update_enable_all_project_mcp_servers(self, value: bool) -> None:
        """更新 enableAllProjectMcpServers 配置"""
        return self.mcp_ops.update_enable_all_project_mcp_servers(value)

    # LSP 相关操作
    async def scan_lsp_servers(
        self, scope: ConfigScope | None = None
    ) -> List[LSPServerInfo]:
        """
        扫描 LSP 服务器配置

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 LSP 服务器。
                   None 表示返回所有作用域的服务器。

        Returns:
            List[LSPServerInfo]: LSP 服务器信息列表
        """
        return await self.lsp_ops.scan_lsp(scope)

    # Markdown 相关操作
    async def load_markdown_content(
        self,
        content_type: str,
        name: str = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> MarkdownContentDTO:
        """加载 Markdown 内容"""
        return await self.markdown_ops.load_markdown_content(content_type, name, scope)

    async def update_markdown_content(
        self,
        content_type: str,
        name: str = None,
        from_md5: str = None,
        content: str = "",
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """更新 Markdown 内容"""
        return await self.markdown_ops.update_markdown_content(
            content_type, name, from_md5, content, scope
        )

    async def rename_markdown_content(
        self,
        content_type: str,
        name: str,
        new_name: str,
        scope: ConfigScope = ConfigScope.project,
        new_scope: ConfigScope = None,
    ) -> None:
        """重命名 Markdown 内容"""
        return await self.markdown_ops.rename_markdown_content(
            content_type, name, new_name, scope, new_scope
        )

    async def save_markdown_content(
        self,
        content_type: str,
        name: str,
        content: str = "",
        scope: ConfigScope = ConfigScope.project,
    ) -> MarkdownContentDTO:
        """保存（新增）Markdown 内容"""
        return await self.markdown_ops.save_markdown_content(
            content_type, name, content, scope
        )

    async def delete_markdown_content(
        self, content_type: str, name: str, scope: ConfigScope = ConfigScope.project
    ) -> None:
        """删除 Markdown 内容"""
        return await self.markdown_ops.delete_markdown_content(
            content_type, name, scope
        )

    # Settings 相关操作
    def scan_settings(self, scope: ConfigScope) -> ClaudeSettingsInfoDTO:
        """
        加载设置配置

        Args:
            scope: 配置作用域，可选值: user, project, local

        Returns:
            ClaudeSettingsDTO: 设置配置对象
        """
        return self.settings_ops.scan_settings(scope)

    def update_settings_values(
        self, scope: ConfigScope, key: str, value: str, value_type: str
    ) -> None:
        """
        更新设置配置中的键值对

        Args:
            scope: 配置作用域，可选值: user, project, local
            key: 配置项的键，支持点号分隔的嵌套键，如 'env.HTTP_PROXY'
            value: 配置项的值（字符串格式）
            value_type: 值类型，可选值: 'string', 'boolean', 'integer', 'array', 'object', 'dict'
        """
        return self.settings_ops.update_settings_values(scope, key, value, value_type)

    def update_settings_scope(
        self,
        old_scope: ConfigScope,
        new_scope: ConfigScope,
        key: str,
    ) -> None:
        """
        更新设置配置项的作用域：从旧作用域移除，在新作用域添加

        Args:
            old_scope: 原配置作用域，可选值: user, project, local
            new_scope: 新配置作用域，可选值: user, project, local
            key: 配置项的键，支持点号分隔的嵌套键，如 'model' 或 'env.HTTP_PROXY'
        """
        return self.settings_ops.update_settings_scope(old_scope, new_scope, key)

    # Hooks CRUD 相关操作
    async def scan_hooks_info(self, scope: ConfigScope | None = None) -> HooksInfo:
        """
        扫描 Hooks 配置

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Hooks。
                   None 表示返回所有作用域的 Hooks。

        Returns:
            HooksInfo: Hooks 配置信息
        """
        return await self.hooks_ops.scan_hooks_info(scope)

    def add_hook(
        self,
        event: HookEvent,
        hook: HookConfig,
        matcher: str = None,
        scope: ConfigScope = ConfigScope.project,
    ) -> None:
        """添加 Hook 配置"""
        return self.hooks_ops.add_hook(event, hook, matcher, scope)

    def remove_hook(
        self,
        hook_id: str,
        scope: ConfigScope = ConfigScope.project,
    ) -> bool:
        """删除 Hook 配置"""
        return self.hooks_ops.remove_hook(hook_id, scope)

    def update_hook(
        self,
        hook_id: str,
        hook: HookConfig,
        scope: ConfigScope = ConfigScope.project,
    ) -> bool:
        """更新 Hook 配置"""
        return self.hooks_ops.update_hook(hook_id, hook, scope)

    def update_disable_all_hooks(self, value: bool) -> None:
        """更新 disableAllHooks 配置"""
        return self.hooks_ops.update_disable_all_hooks(value)

    async def scan_memory(self) -> ClaudeMemoryInfo:
        """加载 CLAUDE.md 配置信息"""
        return await self.markdown_ops.scan_memory()

    async def scan_agents(self, scope: ConfigScope | None = None):
        """
        扫描 Agents 配置信息

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Agents。
                   None 表示返回所有作用域的 Agents。

        Returns:
            List[AgentInfo]: Agent 信息列表
        """
        return await self.markdown_ops.scan_agents(scope)

    async def scan_commands(self, scope: ConfigScope | None = None):
        """
        扫描 Commands 配置信息

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Commands。
                   None 表示返回所有作用域的 Commands。

        Returns:
            List[CommandInfo]: Command 信息列表
        """
        return await self.markdown_ops.scan_commands(scope)

    async def scan_skills(self, scope: ConfigScope | None = None):
        """
        扫描 Skills 配置信息

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 Skills。
                   None 表示返回所有作用域的 Skills。

        Returns:
            List[SkillInfo]: Skill 信息列表
        """
        return await self.markdown_ops.scan_skills(scope)

    # Plugin Marketplace 相关操作
    def scan_plugin_marketplaces(self) -> List[PluginMarketplaceInfo]:
        """扫描已安装的 marketplace 列表"""
        return self.plugin_ops.scan_marketplaces()

    async def scan_plugins(
        self, marketplace_names: Optional[List[str]] = None
    ) -> List[PluginInfo]:
        """
        扫描 marketplace 下的插件列表

        Args:
            marketplace_names: 可选的 marketplace 名称列表，指定时只查询这些 marketplace 的插件

        Returns:
            插件信息列表，按安装数量从大到小排序
        """
        return await self.plugin_ops.scan_plugins(marketplace_names)

    async def install_marketplace(self, source: str) -> ProcessResult:
        """
        安装插件市场

        Args:
            source: 市场来源，可以是 URL、路径或 GitHub 仓库

        Returns:
            ProcessResult: 进程执行结果
        """
        return await self.plugin_ops.install_marketplace(source)

    async def install_plugin(
        self, plugin_name: str, scope: ConfigScope
    ) -> ProcessResult:
        """
        安装插件

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域

        Returns:
            ProcessResult: 进程执行结果
        """
        return await self.plugin_ops.install_plugin(plugin_name, scope)

    async def uninstall_plugin(
        self, plugin_name: str, scope: ConfigScope
    ) -> ProcessResult:
        """
        卸载插件

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域

        Returns:
            ProcessResult: 进程执行结果
        """
        return await self.plugin_ops.uninstall_plugin(plugin_name, scope)

    async def enable_plugin(self, plugin_name: str, scope: ConfigScope) -> None:
        """
        启用插件

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域
        """
        self.plugin_ops.enable_plugin(plugin_name, scope)

    async def disable_plugin(self, plugin_name: str, scope: ConfigScope) -> None:
        """
        禁用插件

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域
        """
        self.plugin_ops.disable_plugin(plugin_name, scope)

    async def move_plugin(
        self, plugin_name: str, old_scope: ConfigScope, new_scope: ConfigScope
    ) -> None:
        """
        移动插件到新的作用域

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            old_scope: 旧的配置作用域
            new_scope: 新的配置作用域
        """
        self.plugin_ops.move_plugin(plugin_name, old_scope, new_scope)

    def read_plugin_readme(
        self, marketplace_name: str, plugin_name: str
    ) -> Optional[str]:
        """
        读取指定插件的 README 文件内容

        Args:
            marketplace_name: marketplace 名称
            plugin_name: 插件名称

        Returns:
            Optional[str]: README 文件内容，如果文件不存在或读取失败返回 None
        """
        return self.plugin_ops.read_plugin_readme_content(marketplace_name, plugin_name)
