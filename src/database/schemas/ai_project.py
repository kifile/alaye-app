"""
AI项目数据模式
"""

import enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field


class AiToolType(str, enum.Enum):
    CLAUDE = "claude"


class AIProjectCreate(BaseModel):
    """创建AI项目的数据模式"""

    project_name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    project_path: Optional[str] = Field(None, description="项目完整路径")
    ai_tools: List[AiToolType] = Field(default=[], description="AI工具列表")
    first_active_at: Optional[datetime] = Field(None, description="首次执行时间")
    last_active_at: Optional[datetime] = Field(None, description="最后执行时间")


class AIProjectUpdate(BaseModel):
    """更新AI项目的数据模式"""

    project_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="项目名称"
    )
    ai_tools: Optional[List[AiToolType]] = Field(None, description="AI工具列表")
    first_active_at: Optional[datetime] = Field(None, description="首次执行时间")
    last_active_at: Optional[datetime] = Field(None, description="最后执行时间")


class AIProjectInDB(BaseModel):
    """数据库中的AI项目模式"""

    id: int = Field(..., description="项目键名")
    project_name: str = Field(..., description="项目名称")
    project_path: Optional[str] = Field(None, description="项目完整路径")
    ai_tools: List[AiToolType] = Field(..., description="AI工具列表")
    first_active_at: Optional[datetime] = Field(
        None, description="首次执行时间", exclude=True
    )
    last_active_at: Optional[datetime] = Field(
        None, description="最后执行时间", exclude=True
    )
    created_at: datetime = Field(..., description="创建时间", exclude=True)
    updated_at: datetime = Field(..., description="更新时间", exclude=True)

    @computed_field
    def first_active_at_str(self) -> Optional[str]:
        return (
            self.first_active_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.first_active_at
            else None
        )

    @computed_field
    def last_active_at_str(self) -> Optional[str]:
        return (
            self.last_active_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_active_at
            else None
        )

    @computed_field
    def created_at_str(self) -> str:
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S")

    @computed_field
    def updated_at_str(self) -> str:
        return self.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    model_config = {"from_attributes": True}
