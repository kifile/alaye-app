"""
Claude 插件市场操作模块
处理 Claude Code 插件市场和插件的扫描、管理等操作
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config.config_service import config_service
from ..utils.process_utils import ProcessResult, run_process
from .markdown_helper import extract_description
from .models import (
    AgentInfo,
    CommandInfo,
    ConfigScope,
    HookConfig,
    HookConfigInfo,
    HookEvent,
    HooksSettings,
    MCPServer,
    MCPServerInfo,
    PluginConfig,
    PluginInfo,
    PluginMarketplaceInfo,
    PluginTools,
    SkillInfo,
)
from .settings_helper import load_config, update_config

logger = logging.getLogger(__name__)


class ClaudePluginOperations:
    """Claude 插件市场操作类"""

    def __init__(self, project_path: Path, user_home: Path | None = None):
        """
        初始化插件市场操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()
        self._claude_command: Optional[str] = None

    async def _get_claude_command(self) -> str:
        """
        获取 claude 命令路径

        从配置中获取 claude.path，并验证 claude.enable 是否为 true。
        如果配置无效或 claude 未启用，抛出异常。

        Returns:
            str: claude 命令的实际路径

        Raises:
            RuntimeError: 当 claude 未启用或路径配置无效时
        """
        # 如果已经缓存过，直接返回
        if self._claude_command is not None:
            return self._claude_command

        # 检查 claude 是否启用
        enable_setting = await config_service.get_setting("claude.enable")
        if enable_setting == "false":
            raise RuntimeError("claude 功能已禁用 (claude.enable = false)")

        # 获取 claude 路径
        claude_path = await config_service.get_setting("claude.path")
        if not claude_path:
            raise RuntimeError("未配置 claude.path")

        # 验证路径是否存在
        path_obj = Path(claude_path)
        if not path_obj.exists():
            raise RuntimeError(f"claude 路径不存在: {claude_path}")

        logger.info(f"使用 claude 命令: {claude_path}")

        # 缓存结果
        self._claude_command = claude_path
        return claude_path

    async def install_marketplace(self, source: str) -> ProcessResult:
        """
        安装插件市场

        通过执行 claude plugin marketplace add 命令来添加新的插件市场。

        Args:
            source: 市场来源，可以是 URL、路径或 GitHub 仓库

        Returns:
            ProcessResult: 进程执行结果，包含成功状态、输出和错误信息

        Example:
            operations = ClaudePluginOperations(project_path)
            result = await operations.install_marketplace("anthropics")
            if result.success:
                print(f"安装成功: {result.stdout}")
        """
        # 获取 claude 命令路径
        claude_cmd = await self._get_claude_command()

        result = run_process(
            [claude_cmd, "plugin", "marketplace", "add", source],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.project_path,
        )

        if result.success:
            logger.info(f"插件市场 {source} 安装成功")
        else:
            logger.error(f"插件市场 {source} 安装失败: {result.error_message}")

        return result

    def scan_marketplaces(self) -> List[PluginMarketplaceInfo]:
        """
        扫描已安装的 marketplace 列表

        从 $HOME/.claude/plugins/known_marketplaces.json 读取已安装的 marketplace 列表

        Returns:
            List[PluginMarketplaceInfo]: marketplace 信息列表
        """
        known_marketplaces_file = (
            self.user_home / ".claude" / "plugins" / "known_marketplaces.json"
        )

        # 使用 settings_helper 加载配置
        marketplaces_config = load_config(known_marketplaces_file)

        marketplaces: List[PluginMarketplaceInfo] = []

        for name, config in marketplaces_config.items():
            try:
                # 直接使用 model_validate 构建整个对象
                marketplace_info = PluginMarketplaceInfo.model_validate(
                    {"name": name, **config}
                )
                marketplaces.append(marketplace_info)
            except Exception as e:
                # 跳过无法解析的 marketplace，记录错误日志
                logger.error(f"Error parsing marketplace '{name}': {e}")
                continue

        return marketplaces

    def _load_enabled_plugins(self) -> Dict[str, Dict[str, bool]]:
        """
        加载已启用的插件列表

        从 user、project、local 的 settings.json 加载 enabledPlugins，
        按照 scope 优先级合并（local > project > user）

        Returns:
            Dict[str, Dict[str, bool]]: 插件键到启用状态和作用域的映射
                格式: {"plugin@marketplace": {"enabled": bool, "scope": ConfigScope}}
        """
        enabled_plugins: Dict[str, Dict[str, bool]] = {}
        scope_priority = [
            ConfigScope.local,
            ConfigScope.project,
            ConfigScope.user,
        ]

        for scope in scope_priority:
            settings_file = self._get_settings_file_by_scope(scope)

            try:
                settings_data = load_config(settings_file)
                scope_enabled_plugins = settings_data.get("enabledPlugins", {})

                for plugin_key, enabled in scope_enabled_plugins.items():
                    # 只有当插件键不存在或当前 scope 优先级更高时才更新
                    if plugin_key not in enabled_plugins:
                        enabled_plugins[plugin_key] = {
                            "enabled": enabled,
                            "scope": scope,
                        }
            except Exception:
                # 如果文件不存在或加载失败，跳过
                continue

        return enabled_plugins

    def _get_settings_file_by_scope(self, scope: ConfigScope) -> Path:
        """
        根据作用域获取 settings 文件路径

        Args:
            scope: 配置作用域

        Returns:
            Path: settings 文件路径

        Raises:
            ValueError: 当 scope 无效时抛出异常
        """
        if scope == ConfigScope.user:
            return self.user_home / ".claude" / "settings.json"
        elif scope == ConfigScope.project:
            return self.project_path / ".claude" / "settings.json"
        elif scope == ConfigScope.local:
            return self.project_path / ".claude" / "settings.local.json"
        else:
            raise ValueError(f"Settings 不支持作用域: {scope}")

    def scan_plugins(
        self, marketplace_names: Optional[List[str]] = None
    ) -> List[PluginInfo]:
        """
        扫描 marketplace 下的插件列表

        遍历每个 marketplace 的 installLocation/.claude-plugin/marketplace.json，
        读取并解析其中的插件列表，并加载安装数量和启用状态

        Args:
            marketplace_names: 可选的 marketplace 名称列表，指定时只查询这些 marketplace 的插件

        Returns:
            List[PluginInfo]: 插件信息列表，按安装数量从大到小排序
        """
        # 加载安装数量缓存
        install_counts = self._load_install_counts()

        # 加载已启用的插件列表
        enabled_plugins = self._load_enabled_plugins()

        # 首先获取所有 marketplace 信息
        marketplaces = self.scan_marketplaces()

        # 如果指定了 marketplace_names，过滤出指定的 marketplace
        if marketplace_names:
            marketplaces = [m for m in marketplaces if m.name in marketplace_names]

        all_plugins: List[PluginInfo] = []

        for marketplace in marketplaces:
            try:
                # 构建 marketplace.json 文件路径
                marketplace_json_path = (
                    Path(marketplace.installLocation)
                    / ".claude-plugin"
                    / "marketplace.json"
                )

                # 使用 load_config 加载配置
                marketplace_data = load_config(marketplace_json_path)

                # 解析插件列表
                plugins = self._parse_plugins(
                    marketplace_data.get("plugins", []),
                    marketplace.name,
                    marketplace.installLocation,
                    install_counts,
                    enabled_plugins,
                    installed_only=False,
                    enabled_only=False,
                )

                all_plugins.extend(plugins)

            except Exception as e:
                # 跳过无法解析的 marketplace，记录错误日志
                logger.error(
                    f"Error parsing plugins from marketplace '{marketplace.name}': {e}"
                )
                continue

        # 排序优先级：installed 降序 > enabled 降序 > 安装数量降序 > name 升序 > marketplace 升序
        all_plugins.sort(
            key=lambda p: (
                -(p.installed or 0),  # installed 降序（已安装的排前面）
                -(p.enabled or 0),  # enabled 降序（已启用的排前面）
                -(p.unique_installs or 0),  # 数量降序（用负数实现）
                p.config.name or "",  # 名称升序
                p.marketplace or "",  # marketplace 升序
            )
        )

        return all_plugins

    def _scan_plugin_tools(
        self,
        plugin_config: PluginConfig,
        marketplace_name: str,
        install_location: str,
        tool_types: Optional[List[str]] = None,
    ) -> Optional[PluginTools]:
        """
        扫描插件的工具能力（commands, skills, agents, hooks, mcp_servers）

        Args:
            plugin_config: 插件配置
            marketplace_name: marketplace 名称
            install_location: marketplace 安装位置
            tool_types: 可选的工具类型列表，例如 ['commands', 'agents']。如果为 None，扫描所有类型。

        Returns:
            Optional[PluginTools]: 插件工具能力，如果扫描失败返回 None
        """
        plugin_name = plugin_config.name
        source = plugin_config.source

        # 确定插件根目录
        plugin_root = None

        if isinstance(source, str):
            # source 是字符串，说明插件已在本地
            # 根据 installLocation + source 的相对路径扫描
            plugin_root = Path(install_location) / source
        elif source is not None:
            # source 是对象，插件可能未安装
            # 从缓存目录获取最大版本
            plugin_root = self._get_plugin_cache_dir(
                marketplace_name, plugin_name, source
            )

        if plugin_root is None or not plugin_root.exists():
            return None

        # 如果未指定 tool_types，扫描所有类型
        if tool_types is None:
            tool_types = ["commands", "skills", "agents", "mcp_servers", "hooks"]

        # 扫描工具能力（只扫描指定类型）
        try:
            return PluginTools(
                commands=(
                    self._scan_plugin_commands(
                        plugin_root, plugin_name, marketplace_name
                    )
                    if "commands" in tool_types
                    else None
                ),
                skills=(
                    self._scan_plugin_skills(plugin_root, plugin_name, marketplace_name)
                    if "skills" in tool_types
                    else None
                ),
                agents=(
                    self._scan_plugin_agents(plugin_root, plugin_name, marketplace_name)
                    if "agents" in tool_types
                    else None
                ),
                mcp_servers=(
                    self._scan_plugin_mcp_servers(
                        plugin_root, plugin_name, marketplace_name
                    )
                    if "mcp_servers" in tool_types
                    else None
                ),
                hooks=(
                    self._scan_plugin_hooks(plugin_root, plugin_name, marketplace_name)
                    if "hooks" in tool_types
                    else None
                ),
            )
        except Exception as e:
            logger.error(f"Error scanning tools for plugin '{plugin_name}': {e}")
            return None

    def _get_plugin_cache_dir(
        self,
        marketplace_name: str,
        plugin_name: str,
        source,
    ) -> Optional[Path]:
        """
        从缓存目录获取插件目录

        从 $HOME/.claude/plugins/cache/$marketplace_name/$plugin_name/$version 中，
        根据最大版本 version 路径获取插件目录

        Args:
            marketplace_name: marketplace 名称
            plugin_name: 插件名称
            source: PluginSource 对象

        Returns:
            Optional[Path]: 插件目录，如果未找到返回 None
        """
        cache_base = (
            self.user_home
            / ".claude"
            / "plugins"
            / "cache"
            / marketplace_name
            / plugin_name
        )

        if not cache_base.exists():
            return None

        # 查找所有版本目录
        version_dirs = [d for d in cache_base.iterdir() if d.is_dir()]

        if not version_dirs:
            return None

        # 找到最大版本（按字典序排序）
        max_version_dir = max(version_dirs, key=lambda d: d.name)

        return max_version_dir

    def _scan_plugin_commands(
        self, plugin_root: Path, plugin_name: str, marketplace_name: str
    ) -> Optional[List[CommandInfo]]:
        """
        扫描插件的 slash commands

        Args:
            plugin_root: 插件根目录
            plugin_name: 插件名称
            marketplace_name: marketplace 名称

        Returns:
            Optional[List[CommandInfo]]: Command 信息列表
        """
        commands_dir = plugin_root / "commands"
        if not commands_dir.exists():
            return None

        commands = []
        for cmd_file in commands_dir.rglob("*.md"):
            try:
                stat = cmd_file.stat()
                # 计算相对于 commands 目录的相对路径
                relative_path = cmd_file.relative_to(commands_dir)
                # 将路径转换为命令名称，使用冒号分隔
                path_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
                command_name = ":".join(path_parts)

                # 提取 description
                description = extract_description(cmd_file)

                commands.append(
                    CommandInfo(
                        name=command_name,
                        scope=ConfigScope.plugin,  # 插件资源使用 plugin 作用域
                        description=description,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        plugin_name=plugin_name,
                        marketplace_name=marketplace_name,
                        file_path=str(cmd_file.absolute()),  # 添加文件绝对路径
                    )
                )
            except Exception as e:
                logger.error(f"Error scanning command file {cmd_file}: {e}")
                continue

        return commands if commands else None

    def _scan_plugin_skills(
        self, plugin_root: Path, plugin_name: str, marketplace_name: str
    ) -> Optional[List[SkillInfo]]:
        """
        扫描插件的 skills

        Args:
            plugin_root: 插件根目录
            plugin_name: 插件名称
            marketplace_name: marketplace 名称

        Returns:
            Optional[List[SkillInfo]]: Skill 信息列表
        """
        skills_dir = plugin_root / "skills"
        if not skills_dir.exists():
            return None

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                try:
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        stat = skill_file.stat()
                        # 提取 description
                        description = extract_description(skill_file)
                        skills.append(
                            SkillInfo(
                                name=skill_dir.name,
                                scope=ConfigScope.plugin,  # 插件资源使用 plugin 作用域
                                description=description,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                plugin_name=plugin_name,
                                marketplace_name=marketplace_name,
                                file_path=str(
                                    skill_dir.absolute()
                                ),  # 记录 skill 目录绝对路径
                            )
                        )
                except Exception as e:
                    logger.error(f"Error scanning skill directory {skill_dir}: {e}")
                    continue

        return skills if skills else None

    def _scan_plugin_agents(
        self, plugin_root: Path, plugin_name: str, marketplace_name: str
    ) -> Optional[List[AgentInfo]]:
        """
        扫描插件的 agents

        Args:
            plugin_root: 插件根目录
            plugin_name: 插件名称
            marketplace_name: marketplace 名称

        Returns:
            Optional[List[AgentInfo]]: Agent 信息列表
        """
        agents_dir = plugin_root / "agents"
        if not agents_dir.exists():
            return None

        agents = []
        for agent_file in agents_dir.rglob("*.md"):
            try:
                stat = agent_file.stat()
                # 提取 description
                description = extract_description(agent_file)
                agents.append(
                    AgentInfo(
                        name=agent_file.stem,
                        scope=ConfigScope.plugin,  # 插件资源使用 plugin 作用域
                        description=description,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        plugin_name=plugin_name,
                        marketplace_name=marketplace_name,
                        file_path=str(agent_file.absolute()),  # 添加文件绝对路径
                    )
                )
            except Exception as e:
                logger.error(f"Error scanning agent file {agent_file}: {e}")
                continue

        return agents if agents else None

    def _scan_plugin_mcp_servers(
        self, plugin_root: Path, plugin_name: str, marketplace_name: str
    ) -> Optional[List[MCPServerInfo]]:
        """
        扫描插件的 MCP servers

        从插件的 .mcp.json 文件中读取 MCP 服务器配置

        Args:
            plugin_root: 插件根目录
            plugin_name: 插件名称
            marketplace_name: marketplace 名称

        Returns:
            Optional[List[MCPServerInfo]]: MCP 服务器信息列表
        """
        mcp_file = plugin_root / ".mcp.json"
        if not mcp_file.exists():
            return None

        try:
            mcp_data = load_config(mcp_file)
            mcp_servers: List[MCPServerInfo] = []

            for name, server_config in mcp_data.items():
                try:
                    mcp_server = MCPServer.model_validate(server_config)
                    mcp_servers.append(
                        MCPServerInfo(
                            name=name,
                            scope=ConfigScope.plugin,  # 插件资源使用 plugin 作用域
                            mcpServer=mcp_server,
                            enabled=True,  # 插件的 MCP 服务器默认启用
                            override=False,
                            plugin_name=plugin_name,
                            marketplace_name=marketplace_name,
                            file_path=str(
                                mcp_file.absolute()
                            ),  # 添加 .mcp.json 文件绝对路径
                        )
                    )
                except Exception as e:
                    logger.error(f"Error parsing MCP server '{name}': {e}")
                    continue

            return mcp_servers if mcp_servers else None
        except Exception as e:
            logger.error(f"Error loading .mcp.json: {e}")
            return None

    def _scan_plugin_hooks(
        self, plugin_root: Path, plugin_name: str, marketplace_name: str
    ) -> Optional[List[HookConfigInfo]]:
        """
        扫描插件的 hooks

        从插件的 hooks/hooks.json 文件中读取 hooks 配置

        Args:
            plugin_root: 插件根目录
            plugin_name: 插件名称
            marketplace_name: marketplace 名称

        Returns:
            Optional[List[HookConfigInfo]]: Hook 配置信息列表
        """
        settings_file = plugin_root / "hooks" / "hooks.json"
        if not settings_file.exists():
            return None

        try:
            settings_data = load_config(settings_file)
            hooks_settings = HooksSettings.model_validate(settings_data)

            if not hooks_settings.hooks:
                return None

            hook_configs = []
            for event, matcher_list in hooks_settings.hooks.items():
                for matcher in matcher_list:
                    for hook_config in matcher.hooks:
                        hook_configs.append(
                            HookConfigInfo(
                                id=self._generate_hook_id(
                                    hook_config,
                                    ConfigScope.plugin,  # 插件资源使用 plugin 作用域
                                    event,
                                    matcher.matcher,
                                ),
                                scope=ConfigScope.plugin,
                                event=event,
                                matcher=matcher.matcher,
                                hook_config=hook_config,
                                plugin_name=plugin_name,
                                marketplace_name=marketplace_name,
                                file_path=str(
                                    settings_file.absolute()
                                ),  # 添加 hooks.json 文件绝对路径
                            )
                        )

            return hook_configs if hook_configs else None
        except Exception as e:
            logger.error(f"Error scanning hooks: {e}")
            return None

    def _generate_hook_id(
        self,
        hook_config: HookConfig,
        scope: ConfigScope,
        event: HookEvent,
        matcher: Optional[str],
    ) -> str:
        """
        生成 Hook 配置的唯一标识

        格式: $type-$scope-$event-$matcher_md5-$content_md5

        Args:
            hook_config: Hook 配置
            scope: 配置作用域
            event: Hook 事件
            matcher: 匹配器模式

        Returns:
            str: Hook ID
        """
        # 生成 matcher 的 hash（空字符串也参与 hash）
        matcher_hash = hashlib.md5((matcher or "").encode()).hexdigest()

        # 获取用于生成 hash 的内容（command 或 prompt）
        content = hook_config.command or hook_config.prompt or ""
        content_hash = hashlib.md5(content.encode()).hexdigest()

        return f"${hook_config.type}-{scope.value}-{event.value}-{matcher_hash}-{content_hash}"

    def _load_install_counts(self) -> Dict[str, int]:
        """
        加载插件安装数量缓存

        从 $HOME/.claude/plugins/install-counts-cache.json 读取安装数量

        Returns:
            Dict[str, int]: 插件键（格式：plugin@marketplace）到安装数量的映射
        """
        install_counts_file = (
            self.user_home / ".claude" / "plugins" / "install-counts-cache.json"
        )

        try:
            cache_data = load_config(install_counts_file)
            counts: Dict[str, int] = {}

            for item in cache_data.get("counts", []):
                plugin_key = item.get("plugin", "")
                unique_installs = item.get("unique_installs")
                if plugin_key and unique_installs is not None:
                    counts[plugin_key] = unique_installs

            return counts
        except Exception:
            # 如果文件不存在或加载失败，返回空字典
            return {}

    def _parse_plugins(
        self,
        plugins_data: List[Dict],
        marketplace_name: str,
        install_location: str,
        install_counts: Dict[str, int],
        enabled_plugins: Dict[str, Dict[str, bool]],
        tool_types: Optional[List[str]] = None,
        installed_only: bool = True,
        enabled_only: bool = True,
    ) -> List[PluginInfo]:
        """
        解析插件数据列表

        Args:
            plugins_data: 从 marketplace.json 读取的插件数据列表
            marketplace_name: 所属 marketplace 名称
            install_location: marketplace 安装位置
            install_counts: 插件安装数量映射
            enabled_plugins: 已启用的插件映射
            tool_types: 可选的工具类型列表，如果指定只扫描这些类型
            installed_only: 是否只返回已安装的插件，默认 True
            enabled_only: 是否只返回已启用的插件，默认 True

        Returns:
            List[PluginInfo]: 解析后的插件信息列表
        """
        plugins: List[PluginInfo] = []

        for plugin_data in plugins_data:
            try:
                plugin_name = plugin_data.get("name", "")
                # 构建插件键：plugin@marketplace
                plugin_key = f"{plugin_name}@{marketplace_name}"

                # 获取插件启用状态
                plugin_status = enabled_plugins.get(plugin_key, {})
                is_enabled = plugin_status.get("enabled")
                enabled_scope = plugin_status.get("scope")

                # 判断是否已安装（在 enabledPlugins 中表示已安装）
                is_installed = is_enabled is not None

                # 应用过滤条件：在扫描工具文件之前就过滤掉不需要的插件
                if installed_only and not is_installed:
                    continue

                if enabled_only and not is_enabled:
                    continue

                # 构建 PluginConfig
                plugin_config = PluginConfig.model_validate(plugin_data)

                # 扫描插件工具能力（传递 tool_types）
                # 只有通过过滤的插件才会扫描文件
                tools = self._scan_plugin_tools(
                    plugin_config, marketplace_name, install_location, tool_types
                )

                # 构建 PluginInfo
                plugin_info = PluginInfo(
                    config=plugin_config,
                    marketplace=marketplace_name,
                    unique_installs=install_counts.get(plugin_key),
                    installed=is_installed,
                    enabled=is_enabled if is_enabled else False,
                    enabled_scope=enabled_scope,
                    tools=tools,
                )
                plugins.append(plugin_info)
            except Exception as e:
                # 跳过无法解析的插件，记录错误日志
                plugin_name = plugin_data.get("name", "unknown")
                logger.error(f"Error parsing plugin '{plugin_name}': {e}")
                continue

        return plugins

    async def install_plugin(
        self, plugin_name: str, scope: ConfigScope
    ) -> ProcessResult:
        """
        安装插件

        通过执行 claude plugin install 命令来安装指定的插件。

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域

        Returns:
            ProcessResult: 进程执行结果，包含成功状态、输出和错误信息

        Example:
            operations = ClaudePluginOperations(project_path)
            result = await operations.install_plugin("code-review@anthropics", ConfigScope.local)
            if result.success:
                print(f"安装成功: {result.stdout}")
        """
        # 获取 claude 命令路径
        claude_cmd = await self._get_claude_command()

        result = run_process(
            [claude_cmd, "plugin", "install", "-s", scope.value, plugin_name],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.project_path,
        )

        if result.success:
            logger.info(f"插件 {plugin_name} 在 {scope.value} 作用域安装成功")
        else:
            logger.error(
                f"插件 {plugin_name} 在 {scope.value} 作用域安装失败: {result.error_message}"
            )

        return result

    async def uninstall_plugin(
        self, plugin_name: str, scope: ConfigScope
    ) -> ProcessResult:
        """
        卸载插件

        通过执行 claude plugin uninstall 命令来卸载指定的插件。

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域

        Returns:
            ProcessResult: 进程执行结果，包含成功状态、输出和错误信息

        Example:
            operations = ClaudePluginOperations(project_path)
            result = await operations.uninstall_plugin("code-review@anthropics", ConfigScope.local)
            if result.success:
                print(f"卸载成功: {result.stdout}")
        """
        # 获取 claude 命令路径
        claude_cmd = await self._get_claude_command()

        result = run_process(
            [claude_cmd, "plugin", "uninstall", "-s", scope.value, plugin_name],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.project_path,
        )

        if result.success:
            logger.info(f"插件 {plugin_name} 在 {scope.value} 作用域卸载成功")
        else:
            logger.error(
                f"插件 {plugin_name} 在 {scope.value} 作用域卸载失败: {result.error_message}"
            )

        return result

    def enable_plugin(self, plugin_name: str, scope: ConfigScope) -> None:
        """
        启用插件

        在指定作用域的 settings.json 中将插件添加到 enabledPlugins。

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域 (user, project, local)

        Raises:
            ValueError: 当配置保存失败时抛出异常

        Example:
            operations = ClaudePluginOperations(project_path)
            operations.enable_plugin("code-review@anthropics", ConfigScope.project)
        """
        settings_file = self._get_settings_file_by_scope(scope)

        # 使用 update_config 将插件设置为启用状态
        # enabledPlugins 是一个字典，键是插件名，值是布尔值
        # 使用 split_key=False 防止 plugin_name 中包含小数点
        try:
            update_config(
                settings_file,
                key_path=["enabledPlugins"],
                key=plugin_name,
                value=True,
                split_key=False,
            )
            logger.info(f"插件 {plugin_name} 已在 {scope.value} 作用域启用")
        except Exception as e:
            logger.error(f"启用插件 {plugin_name} 失败: {e}")
            raise ValueError(f"启用插件 {plugin_name} 失败: {e}") from e

    def disable_plugin(self, plugin_name: str, scope: ConfigScope) -> None:
        """
        禁用插件

        在指定作用域的 settings.json 中将插件从 enabledPlugins 中移除。

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            scope: 配置作用域 (user, project, local)

        Raises:
            ValueError: 当配置保存失败时抛出异常

        Example:
            operations = ClaudePluginOperations(project_path)
            operations.disable_plugin("code-review@anthropics", ConfigScope.project)
        """
        settings_file = self._get_settings_file_by_scope(scope)

        # 使用 update_config 将插件设置为禁用状态（删除键）
        # 使用 split_key=False 防止 plugin_name 中包含小数点
        try:
            update_config(
                settings_file,
                key_path=["enabledPlugins"],
                key=plugin_name,
                value=False,
                split_key=False,
            )
            logger.info(f"插件 {plugin_name} 已在 {scope.value} 作用域禁用")
        except Exception as e:
            logger.error(f"禁用插件 {plugin_name} 失败: {e}")
            raise ValueError(f"禁用插件 {plugin_name} 失败: {e}") from e

    def move_plugin(
        self, plugin_name: str, old_scope: ConfigScope, new_scope: ConfigScope
    ) -> None:
        """
        移动插件到新的作用域

        在旧作用域的 settings.json 中将插件从 enabledPlugins 中移除，
        然后在新作用域的 settings.json 中将插件添加到 enabledPlugins。

        保持插件在新作用域中的启用状态一致。

        Args:
            plugin_name: 插件名称，格式为 "plugin@marketplace"
            old_scope: 旧的配置作用域 (user, project, local)
            new_scope: 新的配置作用域 (user, project, local)

        Raises:
            ValueError: 当配置保存失败时抛出异常

        Example:
            operations = ClaudePluginOperations(project_path)
            operations.move_plugin("code-review@anthropics", ConfigScope.local, ConfigScope.project)
        """
        if old_scope == new_scope:
            logger.info(f"插件 {plugin_name} 已经在 {old_scope} 作用域，无需移动")
            return

        # 获取插件在旧作用域的启用状态
        old_settings_file = self._get_settings_file_by_scope(old_scope)
        old_enabled = False
        try:
            old_settings_data = load_config(old_settings_file)
            old_enabled_plugins = old_settings_data.get("enabledPlugins", {})
            old_enabled = old_enabled_plugins.get(plugin_name, None)
            logger.info(
                f"插件 {plugin_name} 在 {old_scope} 作用域的启用状态: {old_enabled}"
            )
            if old_enabled is None:
                return
        except Exception as e:
            logger.error(f"读取旧作用域配置失败: {e}")
            raise ValueError(f"读取旧作用域配置失败: {e}") from e

        # 获取插件在新作用域的启用状态（如果存在）
        new_settings_file = self._get_settings_file_by_scope(new_scope)
        new_enabled = old_enabled  # 默认保持旧作用域的状态
        try:
            new_settings_data = load_config(new_settings_file)
            new_enabled_plugins = new_settings_data.get("enabledPlugins", {})
            if plugin_name in new_enabled_plugins:
                # 如果新作用域已经有该插件，保持其现有状态
                new_enabled = new_enabled_plugins[plugin_name]
                logger.info(
                    f"插件 {plugin_name} 已存在于 {new_scope} 作用域，现有启用状态: {new_enabled}"
                )
        except Exception as e:
            logger.warning(f"读取新作用域配置失败（可能文件不存在）: {e}")

        # 先在旧作用域中禁用（删除）
        try:
            update_config(
                old_settings_file,
                key_path=["enabledPlugins"],
                key=plugin_name,
                value=None,
                split_key=False,
            )
            logger.info(f"插件 {plugin_name} 已从 {old_scope} 作用域移除")
        except Exception as e:
            logger.error(f"从 {old_scope} 作用域移除插件 {plugin_name} 失败: {e}")
            raise ValueError(
                f"从 {old_scope} 作用域移除插件 {plugin_name} 失败: {e}"
            ) from e

        # 然后在新作用域中设置启用状态
        try:
            update_config(
                new_settings_file,
                key_path=["enabledPlugins"],
                key=plugin_name,
                value=new_enabled,
                split_key=False,
            )
            logger.info(
                f"插件 {plugin_name} 已添加到 {new_scope} 作用域，启用状态: {new_enabled}"
            )
        except Exception as e:
            # 如果新作用域添加失败，尝试回滚（恢复旧作用域的启用状态）
            logger.error(
                f"添加插件 {plugin_name} 到 {new_scope} 作用域失败，尝试回滚: {e}"
            )
            try:
                update_config(
                    old_settings_file,
                    key_path=["enabledPlugins"],
                    key=plugin_name,
                    value=old_enabled,
                    split_key=False,
                )
                logger.info(
                    f"插件 {plugin_name} 已回滚到 {old_scope} 作用域，启用状态: {old_enabled}"
                )
            except Exception as rollback_error:
                logger.error(f"回滚插件 {plugin_name} 失败: {rollback_error}")
            raise ValueError(
                f"添加插件 {plugin_name} 到 {new_scope} 作用域失败: {e}"
            ) from e

    def _scan_plugins_with_tools(
        self,
        tool_types: List[str],
        marketplace_names: Optional[List[str]] = None,
        installed_only: bool = True,
        enabled_only: bool = True,
    ) -> List[PluginInfo]:
        """
        扫描插件的工具信息（支持按需扫描特定类型）

        Args:
            tool_types: 需要扫描的工具类型列表，例如 ['commands', 'agents']
            marketplace_names: 可选的 marketplace 名称列表，指定时只查询这些 marketplace 的插件
            installed_only: 是否只扫描已安装的插件，默认 True
            enabled_only: 是否只扫描已启用的插件，默认 True

        Returns:
            List[PluginInfo]: 插件信息列表
        """
        # 加载已启用的插件列表
        enabled_plugins = self._load_enabled_plugins()

        # 首先获取所有 marketplace 信息
        marketplaces = self.scan_marketplaces()

        # 如果指定了 marketplace_names，过滤出指定的 marketplace
        if marketplace_names:
            marketplaces = [m for m in marketplaces if m.name in marketplace_names]

        all_plugins: List[PluginInfo] = []

        for marketplace in marketplaces:
            try:
                # 构建 marketplace.json 文件路径
                marketplace_json_path = (
                    Path(marketplace.installLocation)
                    / ".claude-plugin"
                    / "marketplace.json"
                )

                # 使用 load_config 加载配置
                marketplace_data = load_config(marketplace_json_path)

                # 解析插件列表（传递过滤条件）
                plugins = self._parse_plugins(
                    marketplace_data.get("plugins", []),
                    marketplace.name,
                    marketplace.installLocation,
                    {},  # install_counts 在这里不需要
                    enabled_plugins,
                    tool_types,  # 传递 tool_types 参数
                    installed_only,  # 传递 installed_only 参数
                    enabled_only,  # 传递 enabled_only 参数
                )

                all_plugins.extend(plugins)

            except Exception as e:
                # 跳过无法解析的 marketplace，记录错误日志
                logger.error(
                    f"Error parsing plugins from marketplace '{marketplace.name}': {e}"
                )
                continue

        return all_plugins

    def get_plugin_commands(
        self, plugin_name_filter: Optional[str] = None
    ) -> List[CommandInfo]:
        """
        获取已启用插件的 commands

        Args:
            plugin_name_filter: 可选的插件名称过滤器。如果指定，只返回该插件的 commands。

        Returns:
            List[CommandInfo]: Command 信息列表
        """
        # 只扫描已安装且已启用插件的 commands，不扫描其他类型
        plugins = self._scan_plugins_with_tools(
            tool_types=["commands"],
            installed_only=True,  # 只扫描已安装的
            enabled_only=True,  # 只扫描已启用的
        )

        all_commands = []
        for plugin in plugins:
            if plugin_name_filter and plugin.config.name != plugin_name_filter:
                continue

            if plugin.tools and plugin.tools.commands:
                all_commands.extend(plugin.tools.commands)

        return all_commands

    def get_plugin_agents(
        self, plugin_name_filter: Optional[str] = None
    ) -> List[AgentInfo]:
        """
        获取已启用插件的 agents

        Args:
            plugin_name_filter: 可选的插件名称过滤器。如果指定，只返回该插件的 agents。

        Returns:
            List[AgentInfo]: Agent 信息列表
        """
        # 只扫描已安装且已启用插件的 agents，不扫描其他类型
        plugins = self._scan_plugins_with_tools(
            tool_types=["agents"],
            installed_only=True,  # 只扫描已安装的
            enabled_only=True,  # 只扫描已启用的
        )

        all_agents = []
        for plugin in plugins:
            if plugin_name_filter and plugin.config.name != plugin_name_filter:
                continue

            if plugin.tools and plugin.tools.agents:
                all_agents.extend(plugin.tools.agents)

        return all_agents

    def get_plugin_skills(
        self, plugin_name_filter: Optional[str] = None
    ) -> List[SkillInfo]:
        """
        获取已启用插件的 skills

        Args:
            plugin_name_filter: 可选的插件名称过滤器。如果指定，只返回该插件的 skills。

        Returns:
            List[SkillInfo]: Skill 信息列表
        """
        # 只扫描已安装且已启用插件的 skills，不扫描其他类型
        plugins = self._scan_plugins_with_tools(
            tool_types=["skills"],
            installed_only=True,  # 只扫描已安装的
            enabled_only=True,  # 只扫描已启用的
        )

        all_skills = []
        for plugin in plugins:
            if plugin_name_filter and plugin.config.name != plugin_name_filter:
                continue

            if plugin.tools and plugin.tools.skills:
                all_skills.extend(plugin.tools.skills)

        return all_skills

    def get_plugin_mcps(
        self, plugin_name_filter: Optional[str] = None
    ) -> List[MCPServerInfo]:
        """
        获取已启用插件的 MCP servers

        Args:
            plugin_name_filter: 可选的插件名称过滤器。如果指定，只返回该插件的 MCP servers。

        Returns:
            List[MCPServerInfo]: MCP 服务器信息列表
        """
        # 只扫描已安装且已启用插件的 mcp_servers，不扫描其他类型
        plugins = self._scan_plugins_with_tools(
            tool_types=["mcp_servers"],
            installed_only=True,  # 只扫描已安装的
            enabled_only=True,  # 只扫描已启用的
        )

        all_mcps = []
        for plugin in plugins:
            if plugin_name_filter and plugin.config.name != plugin_name_filter:
                continue

            if plugin.tools and plugin.tools.mcp_servers:
                all_mcps.extend(plugin.tools.mcp_servers)

        return all_mcps

    def get_plugin_hooks(
        self, plugin_name_filter: Optional[str] = None
    ) -> List[HookConfigInfo]:
        """
        获取已启用插件的 hooks

        Args:
            plugin_name_filter: 可选的插件名称过滤器。如果指定，只返回该插件的 hooks。

        Returns:
            List[HookConfigInfo]: Hook 配置信息列表
        """
        # 只扫描已安装且已启用插件的 hooks，不扫描其他类型
        plugins = self._scan_plugins_with_tools(
            tool_types=["hooks"],
            installed_only=True,  # 只扫描已安装的
            enabled_only=True,  # 只扫描已启用的
        )

        all_hooks = []
        for plugin in plugins:
            if plugin_name_filter and plugin.config.name != plugin_name_filter:
                continue

            if plugin.tools and plugin.tools.hooks:
                all_hooks.extend(plugin.tools.hooks)

        return all_hooks
