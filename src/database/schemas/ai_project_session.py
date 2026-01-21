"""
AI项目会话数据模式
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .ai_project import AiToolType


class AIProjectSessionCreate(BaseModel):
    """创建AI项目会话的数据模式"""

    session_id: str = Field(..., min_length=1, max_length=255, description="会话ID")
    title: Optional[str] = Field(None, max_length=255, description="会话标题")
    project_id: int = Field(..., description="关联的项目ID")
    session_file: Optional[str] = Field(None, description="会话文件路径")
    session_file_md5: Optional[str] = Field(
        None,
        min_length=32,
        max_length=32,
        description="会话文件MD5哈希值（已弃用，保留兼容）",
    )
    file_mtime: Optional[datetime] = Field(None, description="文件修改时间")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    is_agent_session: bool = Field(False, description="是否为Agent会话")
    ai_tool: AiToolType = Field(max_length=50, description="AI工具类型")
    project_path: Optional[str] = Field(None, description="项目路径")
    git_branch: Optional[str] = Field(None, max_length=255, description="Git分支")
    first_active_at: Optional[datetime] = Field(None, description="首次执行时间")
    last_active_at: Optional[datetime] = Field(None, description="最后执行时间")


class AIProjectSessionUpdate(BaseModel):
    """更新AI项目会话的数据模式"""

    session_file_md5: Optional[str] = Field(
        None,
        min_length=32,
        max_length=32,
        description="会话文件MD5哈希值（已弃用，保留兼容）",
    )
    file_mtime: Optional[datetime] = Field(None, description="文件修改时间")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    ai_tool: Optional[AiToolType] = Field(None, description="AI工具类型")
    first_active_at: Optional[datetime] = Field(None, description="首次执行时间")
    last_active_at: Optional[datetime] = Field(None, description="最后执行时间")


class AIProjectSessionInDB(BaseModel):
    """数据库中的AI项目会话模式"""

    id: int = Field(..., description="自增主键")
    session_id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    project_id: int = Field(..., description="关联的项目ID")
    session_file: Optional[str] = Field(None, description="会话文件路径")
    session_file_md5: Optional[str] = Field(
        None, description="会话文件MD5哈希值（已弃用，保留兼容）"
    )
    file_mtime: Optional[datetime] = Field(None, description="文件修改时间")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    is_agent_session: bool = Field(..., description="是否为Agent会话")
    ai_tool: AiToolType = Field(..., description="AI工具类型")
    project_path: Optional[str] = Field(None, description="项目路径")
    git_branch: Optional[str] = Field(None, description="Git分支")
    first_active_at: Optional[datetime] = Field(None, description="首次执行时间")
    last_active_at: Optional[datetime] = Field(None, description="最后执行时间")
    removed: bool = Field(False, description="是否已删除")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}
