"""
PyWebview API Pydantic 模型定义
定义所有 API 方法的输入输出模型，提供字段强校验能力
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..claude.models import (
    ConfigScope,
    HookConfig,
    HookEvent,
    MCPServer,
)

# 定义泛型类型变量
T = TypeVar("T")


class LogLevel(str, Enum):
    """日志级别枚举"""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """事件类型枚举"""

    USER_ACTION = "user_action"
    SYSTEM_UPDATE = "system_update"
    DATA_SYNC = "data_sync"
    ERROR = "error"


class TerminalSize(BaseModel):
    """终端大小模型"""

    rows: int = Field(gt=0, description="终端行数，必须大于0")
    cols: int = Field(gt=0, description="终端列数，必须大于0")


class TerminalMetadata(BaseModel):
    """终端元数据模型"""

    user: Optional[str] = Field(None, description="用户标识")
    purpose: Optional[str] = Field(None, description="终端用途")
    description: Optional[str] = Field(None, description="描述信息")

    model_config = ConfigDict(extra="allow")


# ===== 输入模型 =====


class FileDialogFilter(BaseModel):
    """文件选择器过滤器模型"""

    name: str = Field(description="过滤器名称")
    extensions: List[str] = Field(description="文件扩展名列表")

    model_config = ConfigDict(extra="allow")


class ShowFileDialogRequest(BaseModel):
    """显示文件选择对话框请求模型"""

    title: Optional[str] = Field(default="选择文件", description="对话框标题")
    default_path: Optional[str] = Field(default=None, description="默认打开路径")
    multiple: Optional[bool] = Field(default=False, description="是否允许多选")
    filters: Optional[List[FileDialogFilter]] = Field(
        default=None, description="文件类型过滤器列表"
    )

    model_config = ConfigDict(extra="allow")


class LoadSettingsRequest(BaseModel):
    """加载配置请求模型"""

    keys: Optional[List[str]] = Field(
        default=None, description="要加载的配置键列表，如果为空则加载所有配置"
    )

    model_config = ConfigDict(extra="allow")


class GetSettingRequest(BaseModel):
    """获取单个配置请求模型"""

    key: str = Field(description="配置键名")

    model_config = ConfigDict(extra="allow")


class UpdateSettingRequest(BaseModel):
    """更新配置请求模型"""

    key: str = Field(description="配置键名")
    value: str = Field(description="配置值")

    model_config = ConfigDict(extra="allow")


class ScanClaudeSettingsRequest(BaseModel):
    """扫描Claude设置请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: Optional[ConfigScope] = Field(
        None,
        description="配置作用域（可选，不传入时扫描所有作用域并合并）",
    )

    model_config = ConfigDict(extra="allow")


class UpdateClaudeSettingsValueRequest(BaseModel):
    """更新Claude设置值请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: ConfigScope = Field(
        ...,
        description="配置作用域",
    )
    key: str = Field(..., min_length=1, description="配置项的键，支持点号分隔的嵌套键")
    value: str = Field(..., description="配置项的值（字符串格式）")
    value_type: str = Field(
        ...,
        description="值类型",
        pattern="^(string|boolean|integer|array|object|dict)$",
    )

    model_config = ConfigDict(extra="allow")


class UpdateClaudeSettingsScopeRequest(BaseModel):
    """更新Claude设置作用域请求模型"""

    project_id: int = Field(..., description="项目ID")
    old_scope: ConfigScope = Field(..., description="原配置作用域")
    new_scope: ConfigScope = Field(..., description="新配置作用域")
    key: str = Field(..., min_length=1, description="配置项的键，支持点号分隔的嵌套键")

    model_config = ConfigDict(extra="allow")


class LogRequest(BaseModel):
    """日志请求模型"""

    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    message: str = Field(min_length=1, description="日志消息内容")
    category: Optional[str] = Field(default="frontend", description="日志分类")

    model_config = ConfigDict(extra="allow")


class NewTerminalRequest(BaseModel):
    """创建新终端请求模型"""

    command: Optional[str] = Field(None, description="要执行的命令")
    args: List[str] = Field(default_factory=list, description="命令参数列表")
    work_dir: Optional[str] = Field(None, description="工作目录")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量字典")
    size: Optional[TerminalSize] = Field(None, description="终端大小")
    metadata: Optional[Dict[str, Any]] = Field(None, description="终端元数据")
    terminal_id: Optional[str] = Field(None, description="指定的终端ID")

    @field_validator("env")
    @classmethod
    def validate_env(cls, v):
        if v is None:
            return {}
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        if v is None:
            return {}
        return v


class CloseTerminalRequest(BaseModel):
    """关闭终端请求模型"""

    instance_id: str = Field(min_length=1, description="终端实例ID")

    model_config = ConfigDict(extra="allow")


class WriteToTerminalRequest(BaseModel):
    """写入终端请求模型"""

    instance_id: str = Field(min_length=1, description="终端实例ID")
    data: str = Field(description="要写入的数据")

    model_config = ConfigDict(extra="allow")


class SetTerminalSizeRequest(BaseModel):
    """设置终端大小请求模型"""

    instance_id: str = Field(min_length=1, description="终端实例ID")
    rows: int = Field(gt=0, description="终端行数，必须大于0")
    cols: int = Field(gt=0, description="终端列数，必须大于0")

    model_config = ConfigDict(extra="allow")


# ===== 输出模型 =====


class ShowFileDialogData(BaseModel):
    """显示文件选择对话框数据模型"""

    file_path: Optional[str] = Field(
        default=None, description="选择的文件路径（单选时）"
    )
    file_paths: List[str] = Field(
        default_factory=list, description="选择的文件路径列表（多选时）"
    )
    message: str = Field(description="操作结果消息")

    model_config = ConfigDict(extra="allow")


class LoadSettingsData(BaseModel):
    """加载配置数据模型"""

    settings: Dict[str, str] = Field(description="配置键值对")
    count: int = Field(description="配置项数量")


class ApiResponse(BaseModel, Generic[T]):
    """API 统一响应模型"""

    code: int = Field(description="响应代码，0表示成功，非0表示错误")
    success: bool = Field(description="操作是否成功")
    data: Optional[T] = Field(
        default=None, description="响应数据，成功时包含具体数据，失败时为None"
    )
    error: Optional[str] = Field(default=None, description="错误信息，仅在失败时存在")

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def success_response(cls, data: T) -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(code=0, success=True, data=data)

    @classmethod
    def error_response(cls, code: int, error: str) -> "ApiResponse[None]":
        """创建错误响应"""
        return cls(code=code, success=False, data=None, error=error)


class LogData(BaseModel):
    """日志数据模型"""

    record_info: str = Field(description="日志记录信息")

    model_config = ConfigDict(extra="allow")


# ==================== 扫描相关模型 ====================


class ScanAllProjectsRequest(BaseModel):
    """扫描所有项目请求模型"""

    model_config = ConfigDict(extra="allow")


class ScanSingleProjectRequest(BaseModel):
    """扫描单个项目请求模型"""

    project_id: int = Field(..., description="项目ID")

    model_config = ConfigDict(extra="allow")


class ScanClaudeMemoryRequest(BaseModel):
    """扫描Claude Memory请求模型"""

    project_id: int = Field(..., description="项目ID")

    model_config = ConfigDict(extra="allow")


class ScanClaudeAgentsRequest(BaseModel):
    """扫描Claude Agents请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: Optional[ConfigScope] = Field(None, description="可选的作用域过滤器")

    model_config = ConfigDict(extra="allow")


class ScanClaudeCommandsRequest(BaseModel):
    """扫描Claude Commands请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: Optional[ConfigScope] = Field(None, description="可选的作用域过滤器")

    model_config = ConfigDict(extra="allow")


class ScanClaudeSkillsRequest(BaseModel):
    """扫描Claude Skills请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: Optional[ConfigScope] = Field(None, description="可选的作用域过滤器")

    model_config = ConfigDict(extra="allow")


class ListProjectsRequest(BaseModel):
    """获取项目列表请求模型"""

    model_config = ConfigDict(extra="allow")


class LoadMarkdownContentRequest(BaseModel):
    """加载Markdown内容请求模型"""

    project_id: int = Field(..., description="项目ID")
    content_type: str = Field(
        ...,
        description="内容类型",
        pattern="^(memory|command|agent|hook|skill)$",
    )
    name: Optional[str] = Field(None, description="内容名称")
    scope: Optional[ConfigScope] = Field(None, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class UpdateMarkdownContentRequest(BaseModel):
    """更新Markdown内容请求模型"""

    project_id: int = Field(..., description="项目ID")
    content_type: str = Field(
        ...,
        description="内容类型",
        pattern="^(memory|command|agent|hook|skill)$",
    )
    name: Optional[str] = Field(None, description="内容名称")
    from_md5: str = Field(
        ..., min_length=32, max_length=32, description="当前内容的MD5"
    )
    content: str = Field(..., description="新的内容")
    scope: Optional[ConfigScope] = Field(None, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class RenameMarkdownContentRequest(BaseModel):
    """重命名Markdown内容请求模型"""

    project_id: int = Field(..., description="项目ID")
    content_type: str = Field(
        ...,
        description="内容类型",
        pattern="^(memory|command|agent|hook|skill)$",
    )
    name: str = Field(..., min_length=1, description="当前内容名称")
    new_name: str = Field(..., min_length=1, description="新的内容名称")
    scope: Optional[ConfigScope] = Field(None, description="配置作用域")
    new_scope: Optional[ConfigScope] = Field(None, description="新配置作用域")

    model_config = ConfigDict(extra="allow")


class SaveMarkdownContentRequest(BaseModel):
    """保存Markdown内容请求模型（新增）"""

    project_id: int = Field(..., description="项目ID")
    content_type: str = Field(
        ...,
        description="内容类型",
        pattern="^(memory|command|agent|hook|skill)$",
    )
    name: str = Field(..., min_length=1, description="内容名称")
    content: str = Field(..., description="新的内容")
    scope: Optional[ConfigScope] = Field(None, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class DeleteMarkdownContentRequest(BaseModel):
    """删除Markdown内容请求模型"""

    project_id: int = Field(..., description="项目ID")
    content_type: str = Field(
        ...,
        description="内容类型",
        pattern="^(memory|command|agent|hook|skill)$",
    )
    name: str = Field(..., min_length=1, description="内容名称")
    scope: Optional[ConfigScope] = Field(None, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class IDRequest(BaseModel):
    """ID请求模型"""

    id: int = Field(..., description="项目ID")

    model_config = ConfigDict(extra="allow")


# ==================== MCP 服务器管理相关模型 ====================


class ScanMCPServersRequest(BaseModel):
    """扫描MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: ConfigScope | None = Field(default=None, description="作用域过滤器（可选）")

    model_config = ConfigDict(extra="allow")


class AddMCPServerRequest(BaseModel):
    """添加MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., min_length=1, description="服务器名称")
    server: MCPServer = Field(..., description="MCP服务器配置")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class UpdateMCPServerRequest(BaseModel):
    """更新MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., min_length=1, description="原服务器名称")
    server: MCPServer = Field(..., description="新的MCP服务器配置")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class RenameMCPServerRequest(BaseModel):
    """重命名MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    old_name: str = Field(..., min_length=1, description="原服务器名称")
    new_name: str = Field(..., min_length=1, description="新服务器名称")
    old_scope: ConfigScope = Field(
        default=ConfigScope.project, description="原配置作用域"
    )
    new_scope: Optional[ConfigScope] = Field(
        default=None, description="新配置作用域，None表示保持不变"
    )

    model_config = ConfigDict(extra="allow")


class DeleteMCPServerRequest(BaseModel):
    """删除MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., min_length=1, description="服务器名称")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class EnableMCPServerRequest(BaseModel):
    """启用MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., min_length=1, description="服务器名称")

    model_config = ConfigDict(extra="allow")


class DisableMCPServerRequest(BaseModel):
    """禁用MCP服务器请求模型"""

    project_id: int = Field(..., description="项目ID")
    name: str = Field(..., min_length=1, description="服务器名称")

    model_config = ConfigDict(extra="allow")


class UpdateEnableAllProjectMcpServersRequest(BaseModel):
    """更新enableAllProjectMcpServers请求模型"""

    project_id: int = Field(..., description="项目ID")
    value: bool = Field(..., description="enableAllProjectMcpServers的值")

    model_config = ConfigDict(extra="allow")


# ==================== Hooks 管理相关模型 ====================


class ScanClaudeHooksRequest(BaseModel):
    """扫描Hooks请求模型"""

    project_id: int = Field(..., description="项目ID")
    scope: ConfigScope | None = Field(default=None, description="作用域过滤器（可选）")

    model_config = ConfigDict(extra="allow")


class AddClaudeHookRequest(BaseModel):
    """添加Hook请求模型"""

    project_id: int = Field(..., description="项目ID")
    event: HookEvent = Field(..., description="Hook事件类型")
    hook: HookConfig = Field(..., description="Hook配置")
    matcher: Optional[str] = Field(None, description="匹配器模式")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class RemoveClaudeHookRequest(BaseModel):
    """删除Hook请求模型"""

    project_id: int = Field(..., description="项目ID")
    hook_id: str = Field(..., min_length=1, description="Hook ID")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class UpdateClaudeHookRequest(BaseModel):
    """更新Hook请求模型"""

    project_id: int = Field(..., description="项目ID")
    hook_id: str = Field(..., min_length=1, description="Hook ID")
    hook: HookConfig = Field(..., description="新的Hook配置")
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class UpdateDisableAllHooksRequest(BaseModel):
    """更新disableAllHooks请求模型"""

    project_id: int = Field(..., description="项目ID")
    value: bool = Field(..., description="disableAllHooks的值")

    model_config = ConfigDict(extra="allow")


class ScanClaudePluginMarketplacesRequest(BaseModel):
    """扫描Claude插件市场列表请求模型"""

    project_id: int = Field(..., description="项目ID")

    model_config = ConfigDict(extra="allow")


class ScanClaudePluginsRequest(BaseModel):
    """扫描Claude插件列表请求模型"""

    project_id: int = Field(..., description="项目ID")
    marketplace_names: Optional[List[str]] = Field(
        default=None,
        description="可选的 marketplace 名称列表，指定时只查询这些 marketplace 的插件",
    )

    model_config = ConfigDict(extra="allow")


class InstallClaudePluginRequest(BaseModel):
    """安装Claude插件请求模型"""

    project_id: int = Field(..., description="项目ID")
    plugin_name: str = Field(
        ..., min_length=1, description="插件名称，格式为 plugin@marketplace"
    )
    scope: ConfigScope = Field(
        default=ConfigScope.local, description="配置作用域，默认为 local"
    )

    model_config = ConfigDict(extra="allow")


class UninstallClaudePluginRequest(BaseModel):
    """卸载Claude插件请求模型"""

    project_id: int = Field(..., description="项目ID")
    plugin_name: str = Field(
        ..., min_length=1, description="插件名称，格式为 plugin@marketplace"
    )
    scope: ConfigScope = Field(
        default=ConfigScope.local, description="配置作用域，默认为 local"
    )

    model_config = ConfigDict(extra="allow")


class EnableClaudePluginRequest(BaseModel):
    """启用Claude插件请求模型"""

    project_id: int = Field(..., description="项目ID")
    plugin_name: str = Field(
        ..., min_length=1, description="插件名称，格式为 plugin@marketplace"
    )
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class DisableClaudePluginRequest(BaseModel):
    """禁用Claude插件请求模型"""

    project_id: int = Field(..., description="项目ID")
    plugin_name: str = Field(
        ..., min_length=1, description="插件名称，格式为 plugin@marketplace"
    )
    scope: ConfigScope = Field(default=ConfigScope.project, description="配置作用域")

    model_config = ConfigDict(extra="allow")


class MoveClaudePluginRequest(BaseModel):
    """移动Claude插件到新作用域请求模型"""

    project_id: int = Field(..., description="项目ID")
    plugin_name: str = Field(
        ..., min_length=1, description="插件名称，格式为 plugin@marketplace"
    )
    old_scope: ConfigScope = Field(..., description="旧的配置作用域")
    new_scope: ConfigScope = Field(..., description="新的配置作用域")

    model_config = ConfigDict(extra="allow")


class InstallClaudePluginMarketplaceRequest(BaseModel):
    """安装Claude插件市场请求模型"""

    project_id: int = Field(..., description="项目ID")
    source: str = Field(
        ..., min_length=1, description="市场来源，可以是 URL、路径或 GitHub 仓库"
    )

    model_config = ConfigDict(extra="allow")
