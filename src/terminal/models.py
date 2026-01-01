"""
Terminal Manager Pydantic 模型定义
定义 terminal manager 服务的输入输出模型，提供字段强校验能力
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LogLevel(str, Enum):
    """日志级别枚举"""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


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


# ===== Terminal Manager 专用模型 =====


class NewTerminalManagerRequest(BaseModel):
    """Terminal Manager 新建终端请求模型"""

    command: Optional[str] = Field(
        None, description="要执行的命令，如果为空则使用系统默认shell"
    )
    args: List[str] = Field(default_factory=list, description="命令参数列表")
    work_dir: Optional[str] = Field(None, description="工作目录")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量字典")
    size: Optional[TerminalSize] = Field(None, description="终端大小")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据字典")
    terminal_id: Optional[str] = Field(
        None, description="指定的终端ID，如果为空则自动生成"
    )

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

    model_config = ConfigDict(extra="allow")


class TerminalDTO(BaseModel):
    """终端数据传输对象"""

    instance_id: str = Field(description="终端实例ID")
    status: str = Field(description="终端状态")

    model_config = ConfigDict(extra="allow")


class TerminalManagerException(Exception):
    """Terminal Manager 异常基类"""

    def __init__(self, message: str, instance_id: Optional[str] = None):
        self.message = message
        self.instance_id = instance_id
        super().__init__(self.message)


class TerminalInstanceNotFoundError(TerminalManagerException):
    """终端实例未找到异常"""

    def __init__(self, instance_id: str):
        super().__init__(f"Terminal instance '{instance_id}' not found", instance_id)


class TerminalInstanceAlreadyExistsError(TerminalManagerException):
    """终端实例已存在异常"""

    def __init__(self, instance_id: str):
        super().__init__(
            f"Terminal instance with ID '{instance_id}' already exists", instance_id
        )


class TerminalNotRunningError(TerminalManagerException):
    """终端未运行异常"""

    def __init__(self, instance_id: str):
        super().__init__(
            f"Terminal instance '{instance_id}' is not running", instance_id
        )


class TerminalOperationError(TerminalManagerException):
    """终端操作异常"""

    def __init__(self, message: str, instance_id: Optional[str] = None):
        super().__init__(f"Terminal operation failed: {message}", instance_id)
