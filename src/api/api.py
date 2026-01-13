"""
PyWebview API 核心业务逻辑
提供统一的接口处理逻辑，可供 pywebview 和 FastAPI 共享使用
"""

import asyncio
import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable, List

from ..claude.claude_config_manager import ClaudeConfigManager
from ..claude.models import (
    AgentInfo,
    ClaudeMemoryInfo,
    ClaudeSession,
    ClaudeSessionInfo,
    ClaudeSettingsInfoDTO,
    CommandInfo,
    HooksInfo,
    LSPServerInfo,
    MarkdownContentDTO,
    MCPInfo,
    PluginInfo,
    PluginMarketplaceInfo,
    SkillInfo,
)
from ..config import config_service
from ..database.schemas.ai_project import AIProjectInDB
from ..project.project_service import project_service
from ..terminal.models import (
    NewTerminalManagerRequest,
    TerminalDTO,
)
from ..terminal.terminal_manager_service import get_terminal_manager
from ..utils.process_utils import ProcessResult
from .api_models import (
    AddClaudeHookRequest,
    AddMCPServerRequest,
    ApiResponse,
    CloseTerminalRequest,
    DeleteMarkdownContentRequest,
    DeleteMCPServerRequest,
    DisableClaudePluginRequest,
    DisableMCPServerRequest,
    EnableClaudePluginRequest,
    EnableMCPServerRequest,
    GetSettingRequest,
    IDRequest,
    InstallClaudePluginMarketplaceRequest,
    InstallClaudePluginRequest,
    ListProjectsRequest,
    LoadMarkdownContentRequest,
    LoadSettingsData,
    LoadSettingsRequest,
    LogData,
    LogLevel,
    LogRequest,
    MoveClaudePluginRequest,
    NewTerminalRequest,
    ReadPluginReadmeRequest,
    ReadSessionContentsRequest,
    RemoveClaudeHookRequest,
    RenameMarkdownContentRequest,
    RenameMCPServerRequest,
    SaveMarkdownContentRequest,
    ScanAllProjectsRequest,
    ScanClaudeAgentsRequest,
    ScanClaudeCommandsRequest,
    ScanClaudeHooksRequest,
    ScanClaudeMemoryRequest,
    ScanClaudePluginMarketplacesRequest,
    ScanClaudePluginsRequest,
    ScanClaudeSettingsRequest,
    ScanClaudeSkillsRequest,
    ScanLSPServersRequest,
    ScanMCPServersRequest,
    ScanSessionsRequest,
    ScanSingleProjectRequest,
    SetTerminalSizeRequest,
    UninstallClaudePluginRequest,
    UpdateClaudeHookRequest,
    UpdateClaudeSettingsScopeRequest,
    UpdateClaudeSettingsValueRequest,
    UpdateDisableAllHooksRequest,
    UpdateEnableAllProjectMcpServersRequest,
    UpdateMarkdownContentRequest,
    UpdateMCPServerRequest,
    UpdateSettingRequest,
    WriteToTerminalRequest,
)
from .auto_register import expose_api

# 配置前端专用的日志记录器
frontend_logger = logging.getLogger("frontend")
frontend_logger.setLevel(logging.INFO)

# 配置 API 专用的日志记录器
api_logger = logging.getLogger("api")
api_logger.setLevel(logging.INFO)


def api_logging(func: Callable) -> Callable:
    """
    API日志记录装饰器
    记录API调用的开始、完成、错误信息和执行时间
    """

    @wraps(func)
    async def async_wrapper(self, input_data: Any, *args, **kwargs):
        method_name = func.__name__
        start_time = time.time()

        try:
            api_logger.info(f"API call started: {method_name}")
            api_logger.debug(f"Input data for {method_name}: {input_data}")

            # 执行原方法
            result = await func(self, input_data, *args, **kwargs)

            # 处理返回结果
            execution_time = time.time() - start_time
            api_logger.info(
                f"API call completed: {method_name} (duration={execution_time:.3f}s, success={result.success}, error={result.error})"
            )
            api_logger.debug(
                f"Output data for {method_name}: {result.model_dump() if hasattr(result, 'model_dump') else result}"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            api_logger.error(
                f"API call failed: {method_name} (duration={execution_time:.3f}s, error={str(e)})"
            )
            api_logger.error(f"Error details: {traceback.format_exc()}")
            raise

    @wraps(func)
    def sync_wrapper(self, input_data: Any, *args, **kwargs):
        method_name = func.__name__
        start_time = time.time()

        try:
            api_logger.info(f"API call started: {method_name}")
            api_logger.debug(f"Input data for {method_name}: {input_data}")

            # 执行原方法
            result = func(self, input_data, *args, **kwargs)

            # 处理返回结果
            execution_time = time.time() - start_time
            api_logger.info(
                f"API call completed: {method_name} (duration={execution_time:.3f}s)"
            )
            api_logger.debug(
                f"Output data for {method_name}: {result.model_dump() if hasattr(result, 'model_dump') else result}"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            api_logger.error(
                f"API call failed: {method_name} (duration={execution_time:.3f}s, error={str(e)})"
            )
            api_logger.error(f"Error details: {traceback.format_exc()}")
            raise

    # 根据函数类型返回对应的包装器
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def api_exception_handler(func: Callable) -> Callable:
    """
    API异常处理装饰器
    自动捕获异常并返回标准的错误响应格式
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> ApiResponse:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # 记录错误日志
            frontend_logger.error(f"Error in {func.__name__}: {str(e)}")
            # 返回标准错误响应
            return ApiResponse.error_response(1, str(e))

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> ApiResponse:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录错误日志
            frontend_logger.error(f"Error in {func.__name__}: {str(e)}")
            # 返回标准错误响应
            return ApiResponse.error_response(1, str(e))

    # 根据函数类型返回对应的包装器
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class APICore:
    """API 核心业务逻辑类，提供统一的接口处理逻辑"""

    def __init__(self, event_bus=None):
        """初始化API核心实例"""
        self._event_bus = event_bus  # 事件总线实例，可为None（FastAPI模式）
        self._terminal_manager = get_terminal_manager()

    async def _get_config_manager(self, project_id: str) -> ClaudeConfigManager:
        """
        根据 project_id 获取 ClaudeConfigManager 实例

        Args:
            project_id: 项目ID

        Returns:
            ClaudeConfigManager 实例

        Raises:
            ValueError: 项目不存在或缺少路径信息
        """
        project = await project_service.get_project_by_id(project_id)

        if not project:
            raise ValueError(f"项目 '{project_id}' 不存在")

        project_path = project.project_path
        if not project_path:
            raise ValueError(f"项目 '{project_id}' 缺少路径信息")

        return ClaudeConfigManager(
            project_path, claude_session_path=project.claude_session_path
        )

    @expose_api(LogRequest, LogData, "前端日志输出API")
    @api_exception_handler
    async def log(self, input_data: LogRequest) -> ApiResponse[LogData]:
        """
        前端日志输出核心业务逻辑
        专门处理来自前端的日志请求，统一记录到 frontend.log 文件中

        Args:
            input_data: 经过验证的输入数据，应包含 level 和 message 字段
                - level: 日志级别 (debug, info, warn, warning, error, critical)
                - message: 日志消息内容
                - category: 日志分类 (可选，默认为 "frontend")

        Returns:
            操作结果响应
        """
        category = input_data.category if input_data.category else "frontend"

        # 格式化前端日志消息，包含分类信息
        formatted_message = f"[{category}] {input_data.message}"

        # 根据 level 选择对应的日志方法，使用前端专用日志记录器
        if input_data.level == LogLevel.DEBUG:
            frontend_logger.debug(formatted_message)
        elif input_data.level == LogLevel.INFO:
            frontend_logger.info(formatted_message)
        elif input_data.level in (LogLevel.WARN, LogLevel.WARNING):
            frontend_logger.warning(formatted_message)
        elif input_data.level == LogLevel.ERROR:
            frontend_logger.error(formatted_message)
        elif input_data.level == LogLevel.CRITICAL:
            frontend_logger.critical(formatted_message)

        return ApiResponse.success_response(
            LogData(
                record_info=f"Frontend log recorded: {input_data.level.value} - {input_data.message}"
            )
        )

    @expose_api(NewTerminalRequest, TerminalDTO, "创建新终端API")
    @api_logging
    @api_exception_handler
    async def new_terminal(
        self, input_data: NewTerminalRequest
    ) -> ApiResponse[TerminalDTO]:
        """
        创建新终端的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含以下可选字段：
                - command: 要执行的命令，如果为空则使用系统默认shell
                - args: 命令参数列表
                - work_dir: 工作目录
                - env: 环境变量字典
                - size: 终端大小
                - metadata: 元数据字典
                - terminal_id: 指定的终端ID，如果为空则自动生成

        Returns:
            TerminalDTO 包含终端实例ID和状态信息
        """
        if not self._terminal_manager:
            return ApiResponse.error_response(1, "Terminal manager not initialized")

        # 处理 TerminalSize 类型转换
        # input_data.size 是 api_models.py 中的 TerminalSize 实例
        # 但 NewTerminalManagerRequest 需要的是 pty/models.py 中的 TerminalSize 实例
        size_obj = None
        if input_data.size:
            # 从一个 TerminalSize 实例转换为另一个 TerminalSize 实例
            from src.terminal.models import TerminalSize as PTYTerminalSize

            size_obj = PTYTerminalSize(
                rows=input_data.size.rows, cols=input_data.size.cols
            )

        # 创建 terminal manager 请求模型
        manager_request = NewTerminalManagerRequest(
            command=input_data.command,
            args=input_data.args,
            work_dir=input_data.work_dir,
            env=input_data.env,
            size=size_obj,
            metadata=input_data.metadata,
            terminal_id=input_data.terminal_id,
        )

        # 调用新的 terminal manager 方法
        result = self._terminal_manager.new_terminal(manager_request)
        return ApiResponse.success_response(result)

    @expose_api(CloseTerminalRequest, bool, "关闭终端API")
    @api_logging
    @api_exception_handler
    async def close_terminal(
        self, input_data: CloseTerminalRequest
    ) -> ApiResponse[bool]:
        """
        关闭终端实例的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - instance_id: 终端实例ID

        Returns:
            操作是否成功完成
        """
        if not self._terminal_manager:
            return ApiResponse.error_response(1, "Terminal manager not initialized")

        self._terminal_manager.close_terminal(input_data.instance_id)
        return ApiResponse.success_response(True)

    @expose_api(WriteToTerminalRequest, bool, "向终端写入数据API")
    @api_logging
    @api_exception_handler
    async def write_to_terminal(
        self, input_data: WriteToTerminalRequest
    ) -> ApiResponse[bool]:
        """
        向终端写入数据的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - instance_id: 终端实例ID
                - data: 要写入的数据

        Returns:
            操作是否成功完成
        """
        if not self._terminal_manager:
            return ApiResponse.error_response(1, "Terminal manager not initialized")

        self._terminal_manager.write_to_terminal(
            input_data.instance_id, input_data.data
        )
        return ApiResponse.success_response(True)

    @expose_api(SetTerminalSizeRequest, bool, "设置终端大小API")
    @api_logging
    @api_exception_handler
    async def set_terminal_size(
        self, input_data: SetTerminalSizeRequest
    ) -> ApiResponse[bool]:
        """
        设置终端大小的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - instance_id: 终端实例ID
                - rows: 行数
                - cols: 列数

        Returns:
            操作是否成功完成
        """
        if not self._terminal_manager:
            return ApiResponse.error_response(1, "Terminal manager not initialized")

        self._terminal_manager.set_terminal_size(
            input_data.instance_id, input_data.rows, input_data.cols
        )
        return ApiResponse.success_response(True)

    @expose_api(LoadSettingsRequest, LoadSettingsData, "加载配置API")
    @api_logging
    async def load_settings(
        self, input_data: LoadSettingsRequest
    ) -> ApiResponse[LoadSettingsData]:
        """
        加载配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - keys: 要加载的配置键列表，如果为空则加载所有配置

        Returns:
            LoadSettingsData 包含配置键值对和数量的数据
        """
        # 先加载所有配置
        all_settings = await config_service.get_all_settings()
        all_config_dict = {setting.id: setting.value for setting in all_settings}

        if input_data.keys:
            # 过滤出指定的配置键
            settings = {
                key: value
                for key, value in all_config_dict.items()
                if key in input_data.keys
            }
            count = len(settings)
        else:
            # 返回所有配置
            settings = all_config_dict
            count = len(settings)

        return ApiResponse.success_response(
            LoadSettingsData(settings=settings, count=count)
        )

    @expose_api(GetSettingRequest, str, "获取单个配置API")
    @api_logging
    async def get_setting(self, input_data: GetSettingRequest) -> ApiResponse[str]:
        """
        获取单个配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - key: 配置键名

        Returns:
            配置值字符串
        """
        value = await config_service.get_setting(input_data.key)
        return ApiResponse.success_response(value)

    @expose_api(UpdateSettingRequest, bool, "更新配置API")
    @api_logging
    async def update_setting(
        self, input_data: UpdateSettingRequest
    ) -> ApiResponse[bool]:
        """
        更新配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - key: 配置键名
                - value: 配置值

        Returns:
            操作是否成功完成
        """
        await config_service.set_setting(input_data.key, input_data.value)
        return ApiResponse.success_response(True)

    # ==================== 扫描相关方法 ====================

    @expose_api(ScanAllProjectsRequest, bool, "扫描所有 Claude 项目API")
    @api_logging
    @api_exception_handler
    async def scan_all_projects(
        self, input_data: ScanAllProjectsRequest
    ) -> ApiResponse[bool]:
        """
        扫描所有 Claude 项目的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - force_refresh: 是否强制刷新所有项目

        Returns:
            操作是否成功完成
        """
        # 执行扫描
        await project_service.scan_and_save_all_projects()
        return ApiResponse.success_response(True)

    @expose_api(ScanSingleProjectRequest, bool, "扫描单个 Claude 项目API")
    @api_logging
    @api_exception_handler
    async def scan_single_project(
        self, input_data: ScanSingleProjectRequest
    ) -> ApiResponse[bool]:
        """
        扫描单个 Claude 项目的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID

        Returns:
            操作是否成功完成
        """
        # 执行扫描
        success = await project_service.scan_and_save_single_project(
            input_data.project_id
        )

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"项目 '{input_data.project_id}' 不存在或扫描失败"
            )

    @expose_api(
        ScanClaudeMemoryRequest, ClaudeMemoryInfo, "扫描指定项目的Claude Memory API"
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_memory(
        self, input_data: ScanClaudeMemoryRequest
    ) -> ApiResponse[ClaudeMemoryInfo]:
        """
        扫描指定项目的Claude Memory的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID

        Returns:
            包含Claude Memory扫描结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        memory_info = await config_manager.scan_memory()
        return ApiResponse.success_response(memory_info)

    @expose_api(
        ScanClaudeAgentsRequest, List[AgentInfo], "扫描指定项目的Claude Agents API"
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_agents(
        self, input_data: ScanClaudeAgentsRequest
    ) -> ApiResponse[List[AgentInfo]]:
        """
        扫描指定项目的Claude Agents的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含Claude Agents扫描结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        agents_info = await config_manager.scan_agents(input_data.scope)
        return ApiResponse.success_response(agents_info)

    @expose_api(
        ScanClaudeCommandsRequest,
        List[CommandInfo],
        "扫描指定项目的Claude Commands API",
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_commands(
        self, input_data: ScanClaudeCommandsRequest
    ) -> ApiResponse[List[CommandInfo]]:
        """
        扫描指定项目的Claude Commands的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含Claude Commands扫描结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        commands_info = await config_manager.scan_commands(input_data.scope)
        return ApiResponse.success_response(commands_info)

    @expose_api(
        ScanClaudeSkillsRequest,
        List[SkillInfo],
        "扫描指定项目的Claude Skills API",
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_skills(
        self, input_data: ScanClaudeSkillsRequest
    ) -> ApiResponse[List[SkillInfo]]:
        """
        扫描指定项目的Claude Skills的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含Claude Skills扫描结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        skills_info = await config_manager.scan_skills(input_data.scope)
        return ApiResponse.success_response(skills_info)

    @expose_api(ListProjectsRequest, List[AIProjectInDB], "获取所有 Claude 项目列表API")
    @api_logging
    @api_exception_handler
    async def list_projects(
        self, input_data: ListProjectsRequest
    ) -> ApiResponse[List[AIProjectInDB]]:
        """
        获取所有 Claude 项目列表的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据（此请求无需参数）

        Returns:
            包含所有项目列表的响应，按照 last_active_at 逆序排序
        """
        # 通过 project_service 获取项目列表
        projects = await project_service.list_projects()
        return ApiResponse.success_response(projects)

    @expose_api(IDRequest, AIProjectInDB, "根据 ID 获取单个 Claude 项目API")
    @api_logging
    @api_exception_handler
    async def get_project(self, input_data: IDRequest) -> ApiResponse[AIProjectInDB]:
        """
        根据 ID 获取单个 Claude 项目的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - id: 项目ID

        Returns:
            包含指定项目信息的响应
        """
        # 通过 project_service 获取单个项目
        project = await project_service.get_project_by_id(input_data.id)

        if project:
            return ApiResponse.success_response(project)
        else:
            return ApiResponse.error_response(404, f"项目 '{input_data.id}' 不存在")

    @expose_api(
        LoadMarkdownContentRequest, MarkdownContentDTO, "加载指定项目Markdown内容API"
    )
    @api_logging
    @api_exception_handler
    async def load_claude_markdown_content(
        self, input_data: LoadMarkdownContentRequest
    ) -> ApiResponse[MarkdownContentDTO]:
        """
        加载指定项目Markdown内容的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'hook', 'skill'
                - name: 内容名称
                - scope: 配置作用域

        Returns:
            包含Markdown内容的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        content = await config_manager.load_markdown_content(
            input_data.content_type,
            input_data.name,
            input_data.scope,
        )
        return ApiResponse.success_response(content)

    @expose_api(UpdateMarkdownContentRequest, bool, "更新指定项目Markdown内容API")
    @api_logging
    @api_exception_handler
    async def update_claude_markdown_content(
        self, input_data: UpdateMarkdownContentRequest
    ) -> ApiResponse[bool]:
        """
        更新指定项目Markdown内容的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'hook', 'skill'
                - name: 内容名称
                - from_md5: 期望的当前内容MD5
                - content: 新的内容
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        await config_manager.update_markdown_content(
            input_data.content_type,
            input_data.name,
            input_data.from_md5,
            input_data.content,
            input_data.scope,
        )
        return ApiResponse.success_response(True)

    @expose_api(
        SaveMarkdownContentRequest,
        MarkdownContentDTO,
        "保存（新增）Claude Markdown内容API",
    )
    @api_logging
    @api_exception_handler
    async def save_claude_markdown_content(
        self, input_data: SaveMarkdownContentRequest
    ) -> ApiResponse[MarkdownContentDTO]:
        """
        保存（新增）Claude Markdown内容

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - content_type: 内容类型
                - name: 内容名称
                - content: 新的内容
                - scope: 配置作用域

        Returns:
            ApiResponse[MarkdownContentDTO]: 保存后的内容信息（包含 MD5）
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        content_dto = await config_manager.save_markdown_content(
            input_data.content_type,
            input_data.name,
            input_data.content,
            input_data.scope,
        )
        return ApiResponse.success_response(content_dto)

    @expose_api(
        ScanClaudeSettingsRequest, ClaudeSettingsInfoDTO, "扫描指定项目的Claude设置API"
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_settings(
        self, input_data: ScanClaudeSettingsRequest
    ) -> ApiResponse[ClaudeSettingsInfoDTO]:
        """
        扫描指定项目Claude设置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 配置作用域，可选值: user, project, local（可选，不传入时扫描所有作用域并合并）

        Returns:
            包含Claude设置配置信息（扁平化，包含作用域）的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        settings_info = config_manager.scan_settings(input_data.scope)
        return ApiResponse.success_response(settings_info)

    @expose_api(UpdateClaudeSettingsValueRequest, bool, "更新指定项目的Claude设置值API")
    @api_logging
    @api_exception_handler
    async def update_claude_settings_value(
        self, input_data: UpdateClaudeSettingsValueRequest
    ) -> ApiResponse[bool]:
        """
        更新指定项目Claude设置值的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 配置作用域，可选值: user, project, local
                - key: 配置项的键，支持点号分隔的嵌套键
                - value: 配置项的值（字符串格式）

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.update_settings_values(
            input_data.scope,
            input_data.key,
            input_data.value,
            input_data.value_type,
        )
        return ApiResponse.success_response(True)

    @expose_api(
        UpdateClaudeSettingsScopeRequest, bool, "更新指定项目的Claude设置作用域API"
    )
    @api_logging
    @api_exception_handler
    async def update_claude_settings_scope(
        self, input_data: UpdateClaudeSettingsScopeRequest
    ) -> ApiResponse[bool]:
        """
        更新指定项目Claude设置作用域的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - old_scope: 原配置作用域
                - new_scope: 新配置作用域
                - key: 配置项的键

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.update_settings_scope(
            input_data.old_scope,
            input_data.new_scope,
            input_data.key,
        )
        return ApiResponse.success_response(True)

    @expose_api(RenameMarkdownContentRequest, bool, "重命名指定项目Markdown内容API")
    @api_logging
    @api_exception_handler
    async def rename_claude_markdown_content(
        self, input_data: RenameMarkdownContentRequest
    ) -> ApiResponse[bool]:
        """
        重命名指定项目Markdown内容的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - content_type: 内容类型，可选值: 'memory', 'command', 'agent', 'hook', 'skill'
                - name: 当前内容名称
                - new_name: 新的内容名称
                - scope: 配置作用域
                - new_scope: 新配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        await config_manager.rename_markdown_content(
            input_data.content_type,
            input_data.name,
            input_data.new_name,
            input_data.scope,
            input_data.new_scope,
        )
        return ApiResponse.success_response(True)

    @expose_api(DeleteMarkdownContentRequest, bool, "删除Claude Markdown内容API")
    @api_logging
    @api_exception_handler
    async def delete_claude_markdown_content(
        self, request: DeleteMarkdownContentRequest
    ) -> ApiResponse[bool]:
        """
        删除Claude Markdown内容

        Args:
            request: 删除Markdown内容请求

        Returns:
            ApiResponse[dict]: 删除结果
        """
        config_manager = await self._get_config_manager(request.project_id)
        await config_manager.delete_markdown_content(
            content_type=request.content_type,
            name=request.name,
            scope=request.scope,
        )
        return ApiResponse.success_response(True)

    # ==================== MCP 服务器管理方法 ====================

    @expose_api(ScanMCPServersRequest, MCPInfo, "扫描指定项目的MCP服务器配置API")
    @api_logging
    @api_exception_handler
    async def scan_claude_mcp_servers(
        self, input_data: ScanMCPServersRequest
    ) -> ApiResponse[MCPInfo]:
        """
        扫描指定项目MCP服务器配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含项目配置扫描结果的响应（其中包含MCP配置）
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        mcp_info = await config_manager.scan_mcp_servers(input_data.scope)
        return ApiResponse.success_response(mcp_info)

    @expose_api(AddMCPServerRequest, bool, "添加指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def add_claude_mcp_server(
        self, input_data: AddMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        添加指定项目MCP服务器的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - name: 服务器名称
                - server: MCP服务器配置对象

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.add_mcp_server(
            input_data.name, input_data.server, input_data.scope
        )
        return ApiResponse.success_response(True)

    @expose_api(UpdateMCPServerRequest, bool, "更新指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def update_claude_mcp_server(
        self, input_data: UpdateMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        更新指定项目MCP服务器的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - name: 原服务器名称
                - server: 新的MCP服务器配置对象

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        success = config_manager.update_mcp_server(
            input_data.name, input_data.server, input_data.scope
        )

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"MCP服务器 '{input_data.name}' 不存在"
            )

    @expose_api(DeleteMCPServerRequest, bool, "删除指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def delete_claude_mcp_server(
        self, input_data: DeleteMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        删除指定项目MCP服务器的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - name: 服务器名称
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        success = config_manager.remove_mcp_server(input_data.name, input_data.scope)

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"MCP服务器 '{input_data.name}' 不存在"
            )

    @expose_api(RenameMCPServerRequest, bool, "重命名指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def rename_claude_mcp_server(
        self, input_data: RenameMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        重命名指定项目MCP服务器或更改其作用域的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - old_name: 原服务器名称
                - new_name: 新服务器名称
                - old_scope: 原配置作用域
                - new_scope: 新配置作用域（None表示保持不变）

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        success = config_manager.rename_mcp_server(
            input_data.old_name,
            input_data.new_name,
            input_data.old_scope,
            input_data.new_scope,
        )

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"MCP服务器 '{input_data.old_name}' 不存在"
            )

    @expose_api(EnableMCPServerRequest, bool, "启用指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def enable_claude_mcp_server(
        self, input_data: EnableMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        启用指定项目MCP服务器的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - name: 服务器名称

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.enable_mcp_server(input_data.name)
        return ApiResponse.success_response(True)

    @expose_api(DisableMCPServerRequest, bool, "禁用指定项目的MCP服务器API")
    @api_logging
    @api_exception_handler
    async def disable_claude_mcp_server(
        self, input_data: DisableMCPServerRequest
    ) -> ApiResponse[bool]:
        """
        禁用指定项目MCP服务器的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - name: 服务器名称

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.disable_mcp_server(input_data.name)
        return ApiResponse.success_response(True)

    @expose_api(
        UpdateEnableAllProjectMcpServersRequest,
        bool,
        "更新enableAllProjectMcpServers配置API",
    )
    @api_logging
    @api_exception_handler
    async def update_enable_all_project_mcp_servers(
        self, input_data: UpdateEnableAllProjectMcpServersRequest
    ) -> ApiResponse[bool]:
        """
        更新enableAllProjectMcpServers配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - value: enableAllProjectMcpServers的值

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.update_enable_all_project_mcp_servers(input_data.value)
        return ApiResponse.success_response(True)

    # ==================== LSP 服务器管理方法 ====================

    @expose_api(
        ScanLSPServersRequest, List[LSPServerInfo], "扫描指定项目的LSP服务器配置API"
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_lsp_servers(
        self, input_data: ScanLSPServersRequest
    ) -> ApiResponse[List[LSPServerInfo]]:
        """
        扫描指定项目LSP服务器配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含项目配置扫描结果的响应（其中包含LSP配置）
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        lsp_servers = await config_manager.scan_lsp_servers(input_data.scope)
        return ApiResponse.success_response(lsp_servers)

    # ==================== Hooks 管理方法 ====================

    @expose_api(ScanClaudeHooksRequest, HooksInfo, "扫描指定项目的Hooks配置API")
    @api_logging
    @api_exception_handler
    async def scan_claude_hooks(
        self, input_data: ScanClaudeHooksRequest
    ) -> ApiResponse[HooksInfo]:
        """
        扫描指定项目Hooks配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - scope: 可选的作用域过滤器

        Returns:
            包含项目Hooks配置扫描结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        hooks_info = await config_manager.scan_hooks_info(input_data.scope)
        return ApiResponse.success_response(hooks_info)

    @expose_api(AddClaudeHookRequest, bool, "添加指定项目的Hook API")
    @api_logging
    @api_exception_handler
    async def add_claude_hook(
        self, input_data: AddClaudeHookRequest
    ) -> ApiResponse[bool]:
        """
        添加指定项目Hook的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - event: Hook事件类型
                - hook: Hook配置
                - matcher: 匹配器模式（可选）
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.add_hook(
            input_data.event, input_data.hook, input_data.matcher, input_data.scope
        )
        return ApiResponse.success_response(True)

    @expose_api(RemoveClaudeHookRequest, bool, "删除指定项目的Hook API")
    @api_logging
    @api_exception_handler
    async def remove_claude_hook(
        self, input_data: RemoveClaudeHookRequest
    ) -> ApiResponse[bool]:
        """
        删除指定项目Hook的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - hook_id: Hook ID
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        success = config_manager.remove_hook(input_data.hook_id, input_data.scope)

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"Hook '{input_data.hook_id}' 不存在"
            )

    @expose_api(UpdateClaudeHookRequest, bool, "更新指定项目的Hook API")
    @api_logging
    @api_exception_handler
    async def update_claude_hook(
        self, input_data: UpdateClaudeHookRequest
    ) -> ApiResponse[bool]:
        """
        更新指定项目Hook的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - hook_id: Hook ID
                - hook: 新的Hook配置
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        success = config_manager.update_hook(
            input_data.hook_id, input_data.hook, input_data.scope
        )

        if success:
            return ApiResponse.success_response(True)
        else:
            return ApiResponse.error_response(
                404, f"Hook '{input_data.hook_id}' 不存在"
            )

    @expose_api(UpdateDisableAllHooksRequest, bool, "更新disableAllHooks配置API")
    @api_logging
    @api_exception_handler
    async def update_disable_all_hooks(
        self, input_data: UpdateDisableAllHooksRequest
    ) -> ApiResponse[bool]:
        """
        更新disableAllHooks配置的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - value: disableAllHooks的值

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        config_manager.update_disable_all_hooks(input_data.value)
        return ApiResponse.success_response(True)

    # ==================== Plugin Marketplace 管理方法 ====================

    @expose_api(
        ScanClaudePluginMarketplacesRequest,
        List[PluginMarketplaceInfo],
        "扫描Claude插件市场列表API",
    )
    @api_logging
    @api_exception_handler
    async def scan_claude_plugin_marketplaces(
        self, input_data: ScanClaudePluginMarketplacesRequest
    ) -> ApiResponse[List[PluginMarketplaceInfo]]:
        """
        扫描已安装的Claude插件市场列表的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID

        Returns:
            包含插件市场列表的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        marketplaces = config_manager.scan_plugin_marketplaces()
        return ApiResponse.success_response(marketplaces)

    @expose_api(
        InstallClaudePluginMarketplaceRequest, ProcessResult, "安装Claude插件市场API"
    )
    @api_logging
    @api_exception_handler
    async def install_claude_plugin_marketplace(
        self, input_data: InstallClaudePluginMarketplaceRequest
    ) -> ApiResponse[ProcessResult]:
        """
        安装Claude插件市场的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - source: 市场来源，可以是 URL、路径或 GitHub 仓库

        Returns:
            包含安装结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        result = await config_manager.install_marketplace(input_data.source)
        return ApiResponse.success_response(result)

    @expose_api(ScanClaudePluginsRequest, List[PluginInfo], "扫描Claude插件列表API")
    @api_logging
    @api_exception_handler
    async def scan_claude_plugins(
        self, input_data: ScanClaudePluginsRequest
    ) -> ApiResponse[List[PluginInfo]]:
        """
        扫描Claude插件列表的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - marketplace_names: 可选的 marketplace 名称列表

        Returns:
            包含插件列表的响应，按安装数量从大到小排序
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        plugins = await config_manager.scan_plugins(input_data.marketplace_names)
        return ApiResponse.success_response(plugins)

    @expose_api(InstallClaudePluginRequest, ProcessResult, "安装Claude插件API")
    @api_logging
    @api_exception_handler
    async def install_claude_plugin(
        self, input_data: InstallClaudePluginRequest
    ) -> ApiResponse[ProcessResult]:
        """
        安装Claude插件的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - plugin_name: 插件名称，格式为 plugin@marketplace
                - scope: 配置作用域，默认为 local

        Returns:
            包含安装结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        result = await config_manager.install_plugin(
            input_data.plugin_name, input_data.scope
        )
        return ApiResponse.success_response(result)

    @expose_api(UninstallClaudePluginRequest, ProcessResult, "卸载Claude插件API")
    @api_logging
    @api_exception_handler
    async def uninstall_claude_plugin(
        self, input_data: UninstallClaudePluginRequest
    ) -> ApiResponse[ProcessResult]:
        """
        卸载Claude插件的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - plugin_name: 插件名称，格式为 plugin@marketplace
                - scope: 配置作用域，默认为 local

        Returns:
            包含卸载结果的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        result = await config_manager.uninstall_plugin(
            input_data.plugin_name, input_data.scope
        )
        return ApiResponse.success_response(result)

    @expose_api(EnableClaudePluginRequest, bool, "启用Claude插件API")
    @api_logging
    @api_exception_handler
    async def enable_claude_plugin(
        self, input_data: EnableClaudePluginRequest
    ) -> ApiResponse[bool]:
        """
        启用Claude插件的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - plugin_name: 插件名称，格式为 plugin@marketplace
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        await config_manager.enable_plugin(input_data.plugin_name, input_data.scope)
        return ApiResponse.success_response(True)

    @expose_api(DisableClaudePluginRequest, bool, "禁用Claude插件API")
    @api_logging
    @api_exception_handler
    async def disable_claude_plugin(
        self, input_data: DisableClaudePluginRequest
    ) -> ApiResponse[bool]:
        """
        禁用Claude插件的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - plugin_name: 插件名称，格式为 plugin@marketplace
                - scope: 配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        await config_manager.disable_plugin(input_data.plugin_name, input_data.scope)

        return ApiResponse.success_response(True)

    @expose_api(
        DisableClaudePluginRequest, bool, "移动Claude插件到新作用域的核心业务逻辑"
    )
    @api_logging
    @api_exception_handler
    async def move_claude_plugin(
        self, input_data: MoveClaudePluginRequest
    ) -> ApiResponse[bool]:
        """
        移动Claude插件到新作用域的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - plugin_name: 插件名称，格式为 plugin@marketplace
                - old_scope: 旧的配置作用域
                - new_scope: 新的配置作用域

        Returns:
            操作是否成功完成
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        await config_manager.move_plugin(
            input_data.plugin_name, input_data.old_scope, input_data.new_scope
        )
        return ApiResponse.success_response(True)

    @expose_api(ReadPluginReadmeRequest, str, "读取指定插件README内容API")
    @api_logging
    @api_exception_handler
    async def read_plugin_readme(
        self, input_data: ReadPluginReadmeRequest
    ) -> ApiResponse[str]:
        """
        读取指定插件README内容的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - marketplace_name: marketplace 名称
                - plugin_name: 插件名称

        Returns:
            包含README内容的响应
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        readme_content = config_manager.read_plugin_readme(
            input_data.marketplace_name, input_data.plugin_name
        )

        if readme_content is None:
            return ApiResponse.error_response(
                404, f"插件 '{input_data.plugin_name}' 的 README 文件不存在或读取失败"
            )

        return ApiResponse.success_response(readme_content)

    # ==================== Session 管理方法 ====================

    @expose_api(
        ScanSessionsRequest,
        List[ClaudeSessionInfo],
        "扫描指定项目的Sessions列表API",
    )
    @api_logging
    @api_exception_handler
    async def scan_sessions(
        self, input_data: ScanSessionsRequest
    ) -> ApiResponse[List[ClaudeSessionInfo]]:
        """
        扫描指定项目的Sessions列表的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID

        Returns:
            包含Sessions简要信息列表的响应（不包含 messages）
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        sessions = await config_manager.scan_sessions()
        return ApiResponse.success_response(sessions)

    @expose_api(
        ReadSessionContentsRequest,
        ClaudeSession,
        "读取指定Session的完整内容API",
    )
    @api_logging
    @api_exception_handler
    async def read_session_contents(
        self, input_data: ReadSessionContentsRequest
    ) -> ApiResponse[ClaudeSession]:
        """
        读取指定Session的完整内容的核心业务逻辑

        Args:
            input_data: 经过验证的输入数据，包含：
                - project_id: 项目ID
                - session_id: Session ID

        Returns:
            包含Session完整内容的响应（包含 messages）
        """
        config_manager = await self._get_config_manager(input_data.project_id)
        session = await config_manager.read_session_contents(input_data.session_id)

        if session is None:
            return ApiResponse.error_response(
                404, f"Session '{input_data.session_id}' 不存在"
            )

        return ApiResponse.success_response(session)


# 创建全局 API 核心实例
api_core = APICore()
