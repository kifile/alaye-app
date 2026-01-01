"""
Claude 配置扫描器的数据模型
"""

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, computed_field


class ConfigScope(str, enum.Enum):
    """配置作用域"""

    user = "user"  # 用户全局配置 (~/.claude/, .claude.json)
    project = "project"  # 项目配置 (项目目录/.claude/)
    local = "local"  # 项目本地配置 (项目目录根，如 CLAUDE.local.md，.claude/settings.local.json ,  ~/.claude.json中的项目配置)
    plugin = "plugin"  # 插件配置 (已安装插件提供的资源)


class McpServerType(str, enum.Enum):

    stdio = "stdio"
    http = "http"
    sse = "sse"


# 支持的 Hook 事件类型
class HookEvent(str, enum.Enum):
    PreToolUse = "PreToolUse"
    PermissionRequest = "PermissionRequest"
    PostToolUse = "PostToolUse"
    Notification = "Notification"
    UserPromptSubmit = "UserPromptSubmit"
    Stop = "Stop"
    SubagentStop = "SubagentStop"
    PreCompact = "PreCompact"
    SessionStart = "SessionStart"
    SessionEnd = "SessionEnd"


class FileInfo(BaseModel):
    """文件基本信息"""

    path: str
    exists: bool = False
    size: Optional[int] = None
    modified: Optional[datetime] = Field(None, exclude=True)
    readable: Optional[bool] = None
    error: Optional[str] = None

    @computed_field
    def modified_str(self) -> Optional[str]:
        return self.modified.strftime("%Y-%m-%d %H:%M:%S") if self.modified else None


class ClaudeMemoryInfo(BaseModel):
    """CLAUDE.md 配置信息"""

    project_claude_md: bool = False
    claude_dir_claude_md: bool = False
    local_claude_md: bool = False
    user_global_claude_md: bool = False


class MCPServer(BaseModel):
    """MCP 服务器信息"""

    type: McpServerType = McpServerType.stdio
    command: Optional[str] = None
    args: List[str] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    url: Optional[str] = None  # HTTP 类型的服务器 URL
    headers: Optional[Dict[str, str]] = None  # HTTP 请求头


class MCPServerInfo(BaseModel):
    """MCP 服务器信息（包含名称和作用域）"""

    name: str
    scope: ConfigScope
    mcpServer: MCPServer
    enabled: Optional[bool] = None  # 服务器最终启用状态
    override: bool = False  # 是否被同名的更高优先级服务器覆盖
    plugin_name: Optional[str] = None  # 所属插件名称
    marketplace_name: Optional[str] = None  # 所属 marketplace 名称
    file_path: Optional[str] = None  # .mcp.json 文件绝对路径


class SettingsInfoWithValue(BaseModel):
    """设置信息（包含值和作用域）"""

    value: Optional[bool] = None
    scope: Optional[ConfigScope] = None


class StringInfo(BaseModel):
    """字符串信息（包含值和作用域）"""

    value: Optional[str] = None
    scope: Optional[ConfigScope] = None


class StringListInfo(BaseModel):
    """字符串列表信息（包含值和作用域）"""

    value: Optional[List[str]] = None
    scope: Optional[ConfigScope] = None


class IntInfo(BaseModel):
    """整数信息（包含值和作用域）"""

    value: Optional[int] = None
    scope: Optional[ConfigScope] = None


class EnvVarInfo(BaseModel):
    """环境变量信息"""

    key: str
    value: Optional[str] = None
    scope: Optional[ConfigScope] = None


# MCP 配置扫描结果模型
class UserMcpConfig(BaseModel):
    """User MCP 配置 ($HOME/.claude.json 根路径的 mcpServers)"""

    mcpServers: Dict[str, MCPServer] = Field(default_factory=dict)


class LocalMcpConfig(BaseModel):
    """Local MCP 配置 ($HOME/.claude.json projects 路径下的 mcpServers 和 disabledMcpServers)"""

    mcpServers: Dict[str, MCPServer] = Field(default_factory=dict)
    disabledMcpServers: Optional[List[str]] = None


class ProjectMcpJsonConfig(BaseModel):
    """Project MCP 配置 ($PROJECT/.mcp.json)"""

    mcpServers: Dict[str, MCPServer] = Field(default_factory=dict)


class ProjectSettingsConfig(BaseModel):
    """Project Settings 配置 ($PROJECT/.claude/settings.json)"""

    enableAllProjectMcpServers: Optional[bool] = None
    enabledMcpjsonServers: Optional[List[str]] = None
    disabledMcpjsonServers: Optional[List[str]] = None


class ProjectLocalSettingsConfig(BaseModel):
    """Project Local Settings 配置 ($PROJECT/.claude/settings.local.json)"""

    enableAllProjectMcpServers: Optional[bool] = None
    enabledMcpjsonServers: Optional[List[str]] = None
    disabledMcpjsonServers: Optional[List[str]] = None


class MCPInfo(BaseModel):
    """MCP 服务器配置信息"""

    servers: List[MCPServerInfo] = Field(default_factory=list)
    enable_all_project_mcp_servers: Optional[SettingsInfoWithValue] = None


class SettingsInfo(BaseModel):
    """settings.json 配置信息"""

    shared_settings: Optional[FileInfo] = None
    local_settings: Optional[FileInfo] = None


class CommandInfo(BaseModel):
    """Slash Command 基础信息"""

    name: str
    scope: ConfigScope
    description: Optional[str] = None
    last_modified: Optional[datetime] = Field(None, exclude=True)
    plugin_name: Optional[str] = None  # 所属插件名称
    marketplace_name: Optional[str] = None  # 所属 marketplace 名称
    file_path: Optional[str] = None  # 文件绝对路径

    @computed_field
    def last_modified_str(self) -> Optional[str]:
        return (
            self.last_modified.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_modified
            else None
        )


class AgentInfo(BaseModel):
    """Agent 基础信息"""

    name: str
    scope: ConfigScope
    description: Optional[str] = None
    last_modified: Optional[datetime] = Field(None, exclude=True)
    plugin_name: Optional[str] = None  # 所属插件名称
    marketplace_name: Optional[str] = None  # 所属 marketplace 名称
    file_path: Optional[str] = None  # 文件绝对路径

    @computed_field
    def last_modified_str(self) -> Optional[str]:
        return (
            self.last_modified.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_modified
            else None
        )


class HookInfo(BaseModel):
    """Hook 基础信息"""

    name: str
    command: Optional[str] = None
    last_modified: Optional[datetime] = Field(None, exclude=True)

    @computed_field
    def last_modified_str(self) -> Optional[str]:
        return (
            self.last_modified.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_modified
            else None
        )


class HookConfig(BaseModel):
    """Hook 完整配置信息"""

    type: str  # "command" for bash commands or "prompt" for LLM-based evaluation
    command: Optional[str] = None  # (For type: "command") The bash command to execute
    prompt: Optional[str] = None  # (For type: "prompt") The prompt to send to the LLM
    timeout: Optional[int] = None  # (Optional) How long a hook should run, in seconds


class HookMatcher(BaseModel):
    """Hook Matcher 配置"""

    matcher: Optional[str] = (
        None  # Pattern to match tool names (optional for events without matchers)
    )
    hooks: List[HookConfig] = []  # List of hooks to execute


class HooksSettings(BaseModel):
    """Hooks 设置配置传输对象"""

    hooks: Optional[Dict[HookEvent, List[HookMatcher]]] = (
        None  # 事件名 -> HookMatcher 列表
    )
    disableAllHooks: Optional[bool] = None


class HookConfigInfo(BaseModel):
    id: str  # 格式: $type-md5(command/prompt)
    scope: ConfigScope
    event: HookEvent
    matcher: Optional[str] = None
    hook_config: HookConfig
    plugin_name: Optional[str] = None  # 所属插件名称
    marketplace_name: Optional[str] = None  # 所属 marketplace 名称
    file_path: Optional[str] = None  # hooks.json 文件绝对路径


class HooksInfo(BaseModel):
    """Hooks 配置扫描结果"""

    matchers: Optional[List[HookConfigInfo]] = []
    disable_all_hooks: Optional[SettingsInfoWithValue] = None


class SkillInfo(BaseModel):
    """Skill 基础信息"""

    name: str
    scope: ConfigScope
    description: Optional[str] = None
    last_modified: Optional[datetime] = Field(None, exclude=True)
    plugin_name: Optional[str] = None  # 所属插件名称
    marketplace_name: Optional[str] = None  # 所属 marketplace 名称
    file_path: Optional[str] = None  # Skill 目录绝对路径

    @computed_field
    def last_modified_str(self) -> Optional[str]:
        return (
            self.last_modified.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_modified
            else None
        )


class MarkdownContentDTO(BaseModel):
    """Markdown 内容传输对象"""

    md5: str
    content: str


class PermissionMode(str, enum.Enum):
    default = "default"
    acceptEdits = "acceptEdits"
    plan = "plan"
    bypassPermissions = "bypassPermissions"


class DisableBypassPermissionMode(str, enum.Enum):
    disable = "disable"


# Settings 配置相关模型
class PermissionsConfig(BaseModel):
    """权限配置"""

    allow: Optional[List[str]] = None
    ask: Optional[List[str]] = None
    deny: Optional[List[str]] = None
    additionalDirectories: Optional[List[str]] = None
    defaultMode: Optional[PermissionMode] = None
    disableBypassPermissionsMode: Optional[DisableBypassPermissionMode] = None


class NetworkConfig(BaseModel):
    """网络配置"""

    allowUnixSockets: Optional[List[str]] = None
    allowLocalBinding: Optional[bool] = None
    httpProxyPort: Optional[int] = None
    socksProxyPort: Optional[int] = None


class SandboxConfig(BaseModel):
    """沙盒配置"""

    enabled: Optional[bool] = None
    autoAllowBashIfSandboxed: Optional[bool] = True
    excludedCommands: Optional[List[str]] = None
    allowUnsandboxedCommands: Optional[bool] = None
    enableWeakerNestedSandbox: Optional[bool] = None
    network: Optional[NetworkConfig] = None


class ClaudeSettingsDTO(BaseModel):
    """Claude 设置内容传输对象"""

    # 基础配置
    model: Optional[str] = None
    alwaysThinkingEnabled: Optional[bool] = None
    # 环境变量
    env: Optional[Dict[str, str]] = None
    # 权限配置
    permissions: Optional[PermissionsConfig] = None
    # 沙盒配置
    sandbox: Optional[SandboxConfig] = None


class PermissionsConfigInfo(BaseModel):
    """权限配置信息（包含作用域）"""

    allow: Optional[StringListInfo] = None
    ask: Optional[StringListInfo] = None
    deny: Optional[StringListInfo] = None
    additionalDirectories: Optional[StringListInfo] = None
    defaultMode: Optional[StringInfo] = None
    disableBypassPermissionsMode: Optional[StringInfo] = None


class NetworkConfigInfo(BaseModel):
    """网络配置信息（包含作用域）"""

    allowUnixSockets: Optional[StringListInfo] = None
    allowLocalBinding: Optional[SettingsInfoWithValue] = None
    httpProxyPort: Optional[IntInfo] = None
    socksProxyPort: Optional[IntInfo] = None


class SandboxConfigInfo(BaseModel):
    """沙盒配置信息（包含作用域）"""

    enabled: Optional[SettingsInfoWithValue] = None
    autoAllowBashIfSandboxed: Optional[SettingsInfoWithValue] = None
    excludedCommands: Optional[StringListInfo] = None
    allowUnsandboxedCommands: Optional[SettingsInfoWithValue] = None
    enableWeakerNestedSandbox: Optional[SettingsInfoWithValue] = None
    network: Optional[NetworkConfigInfo] = None


class ClaudeSettingsInfoDTO(BaseModel):
    """Claude 设置信息（扁平化，包含作用域）"""

    settings: Dict[str, Tuple[Any, ConfigScope]] = Field(
        default_factory=dict,
        description="配置项字典，格式: {配置路径: (值, 作用域)}，如 {'model': ('claude-3', ConfigScope.user)}",
    )
    env: List[Tuple[str, str, ConfigScope]] = Field(
        default_factory=list,
        description="环境变量列表，格式: [(变量名, 值, 作用域)]，如 [('HTTP_PROXY', 'http://proxy.com', ConfigScope.user)]",
    )


# Plugin Marketplace 相关模型
class PluginMarketplaceSource(BaseModel):
    """Marketplace 来源配置"""

    source: str  # "github", "url", etc.
    repo: Optional[str] = (
        None  # GitHub repo (e.g., "anthropics/claude-plugins-official")
    )
    url: Optional[str] = None  # URL for non-GitHub sources


class PluginMarketplaceInfo(BaseModel):
    """Marketplace 基本信息"""

    name: str
    source: PluginMarketplaceSource
    installLocation: str
    lastUpdated: Optional[datetime] = Field(None, exclude=True)

    @computed_field
    def lastUpdated_str(self) -> Optional[str]:
        return (
            self.lastUpdated.strftime("%Y-%m-%d %H:%M:%S") if self.lastUpdated else None
        )


class PluginSource(BaseModel):
    """插件来源配置"""

    source: Optional[str] = None  # "url" for remote plugins
    url: Optional[str] = None  # URL for remote plugins


class PluginAuthor(BaseModel):
    """插件作者信息"""

    name: Optional[str] = None
    email: Optional[str] = None


class PluginTools(BaseModel):
    """插件工具能力"""

    commands: Optional[List[CommandInfo]] = None  # 可用的 slash commands
    skills: Optional[List[SkillInfo]] = None  # 可用的 skills
    agents: Optional[List[AgentInfo]] = None  # 可用的 agents
    mcp_servers: Optional[List[MCPServerInfo]] = None  # 可用的 mcp servers
    hooks: Optional[List[HookConfigInfo]] = None  # 可用的 hooks


class PluginConfig(BaseModel):
    """插件配置（来自 marketplace.json）"""

    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[PluginAuthor] = None
    source: Optional[str | PluginSource] = None  # 可以是字符串路径或 PluginSource 对象
    category: Optional[str] = None
    homepage: Optional[str] = None
    tags: Optional[List[str]] = None
    strict: Optional[bool] = None
    lspServers: Optional[Dict[str, Dict]] = None  # LSP 服务器配置


class PluginInfo(BaseModel):
    """插件信息"""

    config: PluginConfig  # 插件配置
    marketplace: Optional[str] = None  # 所属 marketplace 名称
    unique_installs: Optional[int] = None  # 插件安装数量
    installed: Optional[bool] = None  # 是否已安装
    enabled: Optional[bool] = None  # 是否已启用
    enabled_scope: Optional[ConfigScope] = None  # 启用配置的作用域
    tools: Optional[PluginTools] = None  # 插件工具能力
