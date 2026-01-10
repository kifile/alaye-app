"""
MCP 配置操作模块
处理 MCP 服务器的配置、添加、删除、更新等操作
"""

import logging
from pathlib import Path
from typing import Optional

from .models import (
    ConfigScope,
    LocalMcpConfig,
    MCPInfo,
    MCPServer,
    MCPServerInfo,
    ProjectLocalSettingsConfig,
    ProjectMcpJsonConfig,
    ProjectSettingsConfig,
    SettingsInfoWithValue,
    UserMcpConfig,
)
from .settings_helper import (
    add_to_config,
    add_to_project_config,
    load_config,
    load_project_config,
    remove_from_config,
    remove_from_project_config,
    update_config,
    update_project_config,
)

# Configure logger
logger = logging.getLogger("claude")


class ClaudeMCPOperations:
    """Claude MCP 操作类"""

    def __init__(
        self,
        project_path: Path,
        user_home: Path | None = None,
        plugin_ops: Optional["ClaudePluginOperations"] = None,
    ):
        """
        初始化 MCP 操作管理器

        Args:
            project_path: 项目路径
            user_home: 用户主目录路径，可空，默认为系统 User 路径（用于单元测试）
            plugin_ops: 可选的插件操作实例，用于扫描插件提供的 MCP 服务器
        """
        self.project_path = project_path
        self.user_home = user_home if user_home else Path.home()
        self.plugin_ops = plugin_ops

    def scan_mcp(self, scope: ConfigScope | None = None) -> MCPInfo:
        """
        扫描并合并所有 MCP 配置

        扫描以下位置的 MCP 服务器配置：
        1. $HOME/.claude.json 根路径的 mcpServers - user 配置
        2. $HOME/.claude.json 中 projects 路径下的 mcpServers, disabledMcpServers - local 配置
        3. $PROJECT/.mcp.json - project 的 mcp 配置
        4. $PROJECT/.claude/settings.json - project 配置信息
        5. $PROJECT/.claude/settings.local.json - 优先级更高的 local 配置信息

        Args:
            scope: 可选的作用域过滤器。如果指定，只返回该作用域的 MCP 服务器。
                   None 表示返回所有作用域的服务器。

        Returns:
            MCPInfo: 合并后的 MCP 配置信息
        """
        # 根据 scope 决定扫描哪些配置源
        user_config = None
        local_config = None
        project_mcp_json_config = None
        project_settings_config = None
        project_local_settings_config = None

        if scope is None or scope == ConfigScope.user:
            user_config = self._scan_user_mcp_config()

        if scope is None or scope == ConfigScope.local:
            local_config = self._scan_local_mcp_config()

        if scope is None or scope == ConfigScope.project:
            project_mcp_json_config = self._scan_project_mcp_json_config()

        # settings 配置用于获取 enable/disable 状态
        project_settings_config = self._scan_project_settings_config()
        project_local_settings_config = self._scan_project_local_settings_config()

        # 合并配置
        mcp_info = self._combine_mcp_configs(
            user_config,
            local_config,
            project_mcp_json_config,
            project_settings_config,
            project_local_settings_config,
        )

        # 如果 scope 为 None 或为 plugin，扫描已启用插件的 MCP 服务器
        if (scope is None or scope == ConfigScope.plugin) and self.plugin_ops:
            try:
                # 获取已安装的插件列表
                plugins = self.plugin_ops.scan_plugins()

                # 筛选出已启用的插件
                enabled_plugins = [p for p in plugins if p.enabled and p.tools]

                # 从已启用插件中提取 MCP 服务器
                for plugin in enabled_plugins:
                    if plugin.tools and plugin.tools.mcp_servers:
                        mcp_info.servers.extend(plugin.tools.mcp_servers)
            except Exception as e:
                logger.error(f"Failed to scan plugin MCP servers: {e}")

        return mcp_info

    def _scan_user_mcp_config(self) -> UserMcpConfig:
        """
        扫描 User MCP 配置 ($HOME/.claude.json 根路径的 mcpServers)

        Returns:
            UserMcpConfig: User MCP 配置
        """
        home_claude_file = self.user_home / ".claude.json"

        # 使用 settings_helper 加载配置
        home_config = load_config(home_claude_file)

        return UserMcpConfig.model_validate(home_config)

    def _scan_local_mcp_config(self) -> LocalMcpConfig:
        """
        扫描 Local MCP 配置 ($HOME/.claude.json 中当前项目的 mcpServers 和 disabledMcpServers)

        Returns:
            LocalMcpConfig: Local MCP 配置
        """
        home_claude_file = self.user_home / ".claude.json"

        # 使用 settings_helper 加载项目配置
        project_config = load_project_config(home_claude_file, self.project_path)

        return LocalMcpConfig.model_validate(project_config)

    def _scan_project_mcp_json_config(self) -> ProjectMcpJsonConfig:
        """
        扫描 Project MCP JSON 配置 ($PROJECT/.mcp.json)

        Returns:
            ProjectMcpJsonConfig: Project MCP JSON 配置
        """
        project_mcp_file = self.project_path / ".mcp.json"

        # 使用 settings_helper 加载配置
        mcp_config = load_config(project_mcp_file)

        return ProjectMcpJsonConfig.model_validate(mcp_config)

    def _scan_project_settings_config(self) -> ProjectSettingsConfig:
        """
        扫描 Project Settings 配置 ($PROJECT/.claude/settings.json)

        Returns:
            ProjectSettingsConfig: Project Settings 配置
        """
        settings_file = self.project_path / ".claude" / "settings.json"

        # 使用 settings_helper 加载配置
        settings = load_config(settings_file)

        return ProjectSettingsConfig.model_validate(settings)

    def _scan_project_local_settings_config(self) -> ProjectLocalSettingsConfig:
        """
        扫描 Project Local Settings 配置 ($PROJECT/.claude/settings.local.json)

        Returns:
            ProjectLocalSettingsConfig: Project Local Settings 配置
        """
        settings_file = self.project_path / ".claude" / "settings.local.json"

        # 使用 settings_helper 加载配置
        settings = load_config(settings_file)

        return ProjectLocalSettingsConfig.model_validate(settings)

    def _combine_mcp_configs(
        self,
        user_config: UserMcpConfig | None,
        local_config: LocalMcpConfig | None,
        project_mcp_json_config: ProjectMcpJsonConfig | None,
        project_settings_config: ProjectSettingsConfig | None,
        project_local_settings_config: ProjectLocalSettingsConfig | None,
    ) -> MCPInfo:
        """
        合并所有 MCP 配置

        优先级逻辑：
        1. 按 project_settings_config > project_local_settings_config > local_config 的顺序处理 enable/disable 状态
           高优先级的 enable/disable 会覆盖低优先级的状态
        2. 按 local > project > user 的顺序遍历服务器列表
        3. 根据 server_enable_status 和 scope 决定最终 enabled 状态：
           - 如果在 server_enable_status 中有明确状态，使用该状态
           - 如果没有明确状态：
             - user/local scope：默认为 true
             - project scope：取决于 enableAllProjectMcpServers
        4. 检测同名服务器覆盖情况：
           - local > project > user
           - 低优先级的服务器如果与高优先级同名，则标记为 override=True

        Args:
            user_config: User MCP 配置（可为 None）
            local_config: Local MCP 配置（可为 None）
            project_mcp_json_config: Project MCP JSON 配置（可为 None）
            project_settings_config: Project Settings 配置（可为 None）
            project_local_settings_config: Project Local Settings 配置（可为 None）

        Returns:
            MCPInfo: 合并后的 MCP 配置信息
        """
        # 1. 按优先级合并 enable/disable 状态（后面的覆盖前面的）
        server_enable_status: dict[str, bool] = {}

        # 1.1 最低优先级：project_settings_config
        if (
            project_settings_config
            and project_settings_config.disabledMcpjsonServers is not None
        ):
            for name in project_settings_config.disabledMcpjsonServers:
                server_enable_status[name] = False
        if (
            project_settings_config
            and project_settings_config.enabledMcpjsonServers is not None
        ):
            for name in project_settings_config.enabledMcpjsonServers:
                server_enable_status[name] = True

        # 1.2 中等优先级：project_local_settings_config（会覆盖上面的）
        if (
            project_local_settings_config
            and project_local_settings_config.disabledMcpjsonServers is not None
        ):
            for name in project_local_settings_config.disabledMcpjsonServers:
                server_enable_status[name] = False
        if (
            project_local_settings_config
            and project_local_settings_config.enabledMcpjsonServers is not None
        ):
            for name in project_local_settings_config.enabledMcpjsonServers:
                server_enable_status[name] = True

        # 1.3 最高优先级：local_config.disabledMcpServers（会覆盖上面的）
        if local_config and local_config.disabledMcpServers is not None:
            for name in local_config.disabledMcpServers:
                server_enable_status[name] = False

        # 2. 确定 enableAllProjectMcpServers 的最终值和作用域
        enable_all_info = self._determine_enable_all_project_mcp_servers(
            project_settings_config, project_local_settings_config
        )

        # 3. 按 local > project > user 的顺序遍历服务器列表
        servers = []

        # 用于追踪已出现的服务器名称（按优先级）
        seen_server_names: set[str] = set()

        # 3.1 处理 Local 服务器 (scope=local, 最高优先级)
        if local_config:
            for name, server in local_config.mcpServers.items():
                enabled = self._get_server_enabled_status(
                    name=name,
                    scope=ConfigScope.local,
                    server_enable_status=server_enable_status,
                    enable_all=None,
                )
                servers.append(
                    MCPServerInfo(
                        name=name,
                        scope=ConfigScope.local,
                        mcpServer=server,
                        enabled=enabled,
                        override=False,  # 最高优先级，不会被覆盖
                    )
                )
                seen_server_names.add(name)

        # 3.2 处理 Project 服务器 (scope=project, 中等优先级)
        if project_mcp_json_config:
            for name, server in project_mcp_json_config.mcpServers.items():
                enabled = self._get_server_enabled_status(
                    name=name,
                    scope=ConfigScope.project,
                    server_enable_status=server_enable_status,
                    enable_all=enable_all_info.value,
                )
                servers.append(
                    MCPServerInfo(
                        name=name,
                        scope=ConfigScope.project,
                        mcpServer=server,
                        enabled=enabled,
                        override=name in seen_server_names,  # 检查是否被 local 覆盖
                    )
                )
                seen_server_names.add(name)

        # 3.3 处理 User 服务器 (scope=user, 最低优先级)
        if user_config:
            for name, server in user_config.mcpServers.items():
                enabled = self._get_server_enabled_status(
                    name=name,
                    scope=ConfigScope.user,
                    server_enable_status=server_enable_status,
                    enable_all=None,
                )
                servers.append(
                    MCPServerInfo(
                        name=name,
                        scope=ConfigScope.user,
                        mcpServer=server,
                        enabled=enabled,
                        override=name
                        in seen_server_names,  # 检查是否被 local 或 project 覆盖
                    )
                )

        return MCPInfo(
            servers=servers,
            enable_all_project_mcp_servers=enable_all_info,
        )

    def _get_server_enabled_status(
        self,
        name: str,
        scope: ConfigScope,
        server_enable_status: dict[str, bool],
        enable_all: bool | None,
    ) -> bool:
        """
        获取服务器的启用状态

        规则：
        1. 如果在 server_enable_status 中有明确状态，使用该状态
        2. 如果没有明确状态：
           - user /local scope：默认为 true
           - project scope：
             - enable_all 为 False：禁用（需要显式启用）
             - enable_all 为 True 或 None：启用（默认行为）

        Args:
            name: 服务器名称
            scope: 服务器作用域
            server_enable_status: 服务器启用状态字典
            enable_all: enableAllProjectMcpServers 的值（仅对 project scope 有效）
                         - False: 禁用所有 project MCP 服务器
                         - True: 启用所有 project MCP 服务器
                         - None: 未配置，默认启用（与 True 行为相同）

        Returns:
            bool: 服务器是否启用
        """
        # 优先使用明确的状态
        if name in server_enable_status:
            return server_enable_status[name]

        # 没有明确状态，根据 scope 决定
        if scope == ConfigScope.project:
            # project scope：只有明确设置为 False 时才禁用，其他情况都启用
            return enable_all is not False

        # user /local scope 默认为 true
        return True

    def _determine_enable_all_project_mcp_servers(
        self,
        project_settings: ProjectSettingsConfig | None,
        project_local_settings: ProjectLocalSettingsConfig | None,
    ) -> SettingsInfoWithValue:
        """
        确定 enableAllProjectMcpServers 的最终值和作用域

        Args:
            project_settings: Project Settings 配置（可为 None）
            project_local_settings: Project Local Settings 配置（可为 None）

        Returns:
            SettingsInfoWithValue: 包含值和作用域的设置信息
        """
        # settings.local.json 优先级更高
        if (
            project_local_settings
            and project_local_settings.enableAllProjectMcpServers is not None
        ):
            return SettingsInfoWithValue(
                value=project_local_settings.enableAllProjectMcpServers,
                scope=ConfigScope.local,
            )

        # settings.json 次之
        if project_settings and project_settings.enableAllProjectMcpServers is not None:
            return SettingsInfoWithValue(
                value=project_settings.enableAllProjectMcpServers,
                scope=ConfigScope.project,
            )

        # 都未设置，返回 None
        return SettingsInfoWithValue(value=None, scope=None)

    def _load_mcp_config_by_scope(self, scope: ConfigScope, name: str) -> dict:
        """
        根据作用域加载 MCP 配置中的 mcpServers 字典或特定服务器配置

        Args:
            scope: 配置作用域
            name: 返回该服务器的配置

        Returns:
            dict

        Note:
            对于 project scope，从 .mcp.json 中加载
            对于 user scope，从 ~/.claude.json 中加载
            对于 local scope，从 ~/.claude.json 中当前项目配置中加载
        """
        if scope == ConfigScope.project:
            mcp_file = self.project_path / ".mcp.json"
            config = load_config(mcp_file)
            mcp_servers = config.get("mcpServers", {})

        elif scope == ConfigScope.user:
            claude_file = self.user_home / ".claude.json"
            config = load_config(claude_file)
            mcp_servers = config.get("mcpServers", {})

        elif scope == ConfigScope.local:
            claude_file = self.user_home / ".claude.json"
            project_config = load_project_config(claude_file, self.project_path)
            mcp_servers = project_config.get("mcpServers", {}) if project_config else {}

        else:
            raise ValueError(f"不支持的作用域: {scope}")

        return mcp_servers.get(name, {})

    def remove_mcp_server(
        self, name: str, scope: ConfigScope = ConfigScope.project
    ) -> bool:
        """
        删除 MCP 服务器

        Args:
            name: 服务器名称
            scope: 配置作用域，默认为 project

        Returns:
            bool: 是否成功删除
        """
        # 使用 update_config 或 update_project_config 删除服务器
        # 使用 split_key=False 避免名称中包含 "." 导致的解析问题
        if scope == ConfigScope.project:
            mcp_file = self.project_path / ".mcp.json"
            update_config(
                mcp_file, key_path=["mcpServers"], key=name, value=None, split_key=False
            )
        elif scope == ConfigScope.user:
            claude_file = self.user_home / ".claude.json"
            update_config(
                claude_file,
                key_path=["mcpServers"],
                key=name,
                value=None,
                split_key=False,
            )
        elif scope == ConfigScope.local:
            claude_file = self.user_home / ".claude.json"
            success = update_project_config(
                claude_file,
                self.project_path,
                name,
                None,
                key_path=["mcpServers"],
                split_key=False,
            )
            return success

        return True

    def add_mcp_server(
        self, name: str, server: MCPServer, scope: ConfigScope = ConfigScope.project
    ) -> None:
        """
        添加 MCP 服务器

        Args:
            name: 服务器名称
            server: MCP 服务器配置信息
            scope: 配置作用域，默认为 project

        Raises:
            ValueError: 当服务器名称已存在时抛出异常
        """
        # 检查同名服务器是否已存在
        existing = self._load_mcp_config_by_scope(scope, name)
        if existing:
            raise ValueError(f"作用域 {scope} 中已存在服务器 '{name}'")

        server_config = server.model_dump(exclude_none=True)

        if scope == ConfigScope.project:
            mcp_file = self.project_path / ".mcp.json"
            update_config(
                mcp_file,
                key_path=["mcpServers"],
                key=name,
                value=server_config,
                split_key=False,
            )
        elif scope == ConfigScope.user:
            claude_file = self.user_home / ".claude.json"
            update_config(
                claude_file,
                key_path=["mcpServers"],
                key=name,
                value=server_config,
                split_key=False,
            )
        elif scope == ConfigScope.local:
            claude_file = self.user_home / ".claude.json"
            success = update_project_config(
                claude_file,
                self.project_path,
                name,
                server_config,
                key_path=["mcpServers"],
                split_key=False,
            )
            if not success:
                raise ValueError(f"无法在作用域 {scope} 中添加服务器，项目配置不存在")

    def update_mcp_server(
        self, name: str, server: MCPServer, scope: ConfigScope = ConfigScope.project
    ) -> bool:
        """
        更新 MCP 服务器配置

        Args:
            name: 要更新的服务器名称
            server: 新的 MCP 服务器配置信息
            scope: 配置作用域，默认为 project

        Returns:
            bool: 是否成功更新

        Note:
            此方法不支持重命名和更改作用域。如需重命名或更改作用域，请使用 rename_mcp_server 方法。
        """
        server_config = server.model_dump(exclude_none=True)

        if scope == ConfigScope.project:
            mcp_file = self.project_path / ".mcp.json"
            update_config(
                mcp_file,
                key_path=["mcpServers"],
                key=name,
                value=server_config,
                split_key=False,
            )
        elif scope == ConfigScope.user:
            claude_file = self.user_home / ".claude.json"
            update_config(
                claude_file,
                key_path=["mcpServers"],
                key=name,
                value=server_config,
                split_key=False,
            )
        elif scope == ConfigScope.local:
            claude_file = self.user_home / ".claude.json"
            success = update_project_config(
                claude_file,
                self.project_path,
                name,
                server_config,
                key_path=["mcpServers"],
                split_key=False,
            )
            return success

        return True

    def rename_mcp_server(
        self,
        old_name: str,
        new_name: str,
        old_scope: ConfigScope = ConfigScope.project,
        new_scope: ConfigScope = None,
    ) -> bool:
        """
        重命名 MCP 服务器或更改其作用域

        操作分为两步：
        1. 使用 add_mcp_server 添加到新的作用域和名称
        2. 使用 remove_mcp_server 从旧的作用域和名称删除

        Args:
            old_name: 原服务器名称
            new_name: 新服务器名称
            old_scope: 原配置作用域，默认为 project
            new_scope: 新配置作用域，None 表示保持不变

        Returns:
            bool: 是否成功重命名

        Raises:
            ValueError: 当目标作用域中已存在同名服务器或源服务器不存在时抛出异常
        """
        if new_scope is None:
            new_scope = old_scope

        # 如果名称和作用域都没有变化，直接返回
        if old_name == new_name and old_scope == new_scope:
            return True

        # 1. 获取旧的 MCP 服务器配置
        server_dict = self._load_mcp_config_by_scope(old_scope, old_name)

        if not server_dict:
            raise ValueError(f"作用域 {old_scope} 中不存在服务器 '{old_name}'")

        # 将字典转换为 MCPServer 对象
        mcp_server = MCPServer.model_validate(server_dict)

        # 2. 添加到新的作用域和名称（会检查同名冲突）
        self.add_mcp_server(new_name, mcp_server, new_scope)

        # 3. 从旧的作用域和名称删除（仅在添加成功后执行）
        self.remove_mcp_server(old_name, old_scope)
        return True

    def update_enable_all_project_mcp_servers(self, value: bool) -> None:
        """
        更新 MCP 设置中的 enableAllProjectMcpServers 配置

        直接操作 settings.local.json 文件中的 enableAllProjectMcpServers 值。

        Args:
            value: enableAllProjectMcpServers 的布尔值

        Raises:
            ValueError: 当保存配置失败时抛出异常
        """
        settings_file = self.project_path / ".claude" / "settings.local.json"
        # 使用 settings_helper 进行增量更新
        update_config(
            settings_file, key_path=None, key="enableAllProjectMcpServers", value=value
        )

    def disable_mcp_server(self, name: str) -> None:
        """
        禁用 MCP 服务器

        优先将服务器名称添加到 local_config 的 disabledMcpServers 中。
        如果 ~/.claude.json 中不存在当前项目配置，则添加到 settings.local.json 的 disabledMcpjsonServers 中。

        Args:
            name: MCP 服务器名称

        Note:
            此操作会修改以下配置文件之一：
            - ~/.claude.json 中当前项目的 disabledMcpServers（如果项目配置存在）
            - $PROJECT/.claude/settings.local.json 中的 disabledMcpjsonServers（如果项目配置不存在）
        """
        claude_file = self.user_home / ".claude.json"

        # 尝试使用 add_to_project_config 添加到项目配置
        success = add_to_project_config(
            claude_file,
            self.project_path,
            "disabledMcpServers",
            name,
        )

        if not success:
            # ~/.claude.json 中不存在当前项目配置，使用 settings.local.json
            settings_file = self.project_path / ".claude" / "settings.local.json"
            add_to_config(
                settings_file, key_path=None, key="disabledMcpjsonServers", value=name
            )

    def enable_mcp_server(self, name: str) -> None:
        """
        启用 MCP 服务器

        执行以下操作：
        1. 从 local_config 的 disabledMcpServers 中移除
        2. 在 project_settings_config 和 project_local_settings_config 中：
           - 如果 disabledMcpjsonServers 不为 None，移除对应的 mcp
           - 如果 enabledMcpjsonServers 不为 None，且不存在当前 mcp，添加当前 mcp

        Args:
            name: MCP 服务器名称

        Note:
            此操作会修改以下配置文件：
            - ~/.claude.json 中当前项目的 disabledMcpServers
            - $PROJECT/.claude/settings.json 中的 enabledMcpjsonServers/disabledMcpjsonServers
            - $PROJECT/.claude/settings.local.json 中的 enabledMcpjsonServers/disabledMcpjsonServers
        """
        # 1. 处理 local_config 的 disabledMcpServers
        claude_file = self.user_home / ".claude.json"

        # 使用 remove_from_project_config 从项目配置中移除
        remove_from_project_config(
            claude_file,
            self.project_path,
            "disabledMcpServers",
            name,
        )

        # 2. 处理 project_settings_config 和 project_local_settings_config
        self._enable_mcp_server_in_settings(name, False)  # settings.json
        self._enable_mcp_server_in_settings(name, True)  # settings.local.json

    def _enable_mcp_server_in_settings(self, name: str, is_local: bool) -> None:
        """
        在 settings 文件中启用 MCP 服务器

        Args:
            name: MCP 服务器名称
            is_local: 是否为 settings.local.json（False 表示 settings.json）
        """
        settings_file = (
            self.project_path / ".claude" / "settings.local.json"
            if is_local
            else self.project_path / ".claude" / "settings.json"
        )

        if not settings_file.exists():
            return

        remove_from_config(
            settings_file,
            key_path=None,
            key="disabledMcpjsonServers",
            value=name,
        )

        add_to_config(
            settings_file,
            key_path=None,
            key="enabledMcpjsonServers",
            value=name,
        )
