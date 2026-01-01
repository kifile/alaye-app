"""
通用数据结构
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class PagedData(BaseModel, Generic[T]):
    """分页数据结构"""

    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
