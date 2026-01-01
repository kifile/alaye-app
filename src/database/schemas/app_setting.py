"""
应用设置数据模式
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AppSettingCreate(BaseModel):
    """创建应用设置的数据模式"""

    id: str = Field(..., min_length=1, max_length=255, description="设置键名")
    value: Optional[str] = Field(None, description="设置值")


class AppSettingUpdate(BaseModel):
    """更新应用设置的数据模式"""

    value: Optional[str] = Field(None, description="设置值")


class AppSettingInDB(BaseModel):
    """数据库中的应用设置模式"""

    id: str = Field(..., description="设置键名")
    value: Optional[str] = Field(None, description="设置值")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}
