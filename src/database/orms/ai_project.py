"""
AI项目ORM模型
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func

from .base import Base


class AIProject(Base):
    """
    AI项目模型

    存储 Claude 扫描到的项目信息
    """

    __tablename__ = "ai_projects"

    # 项目键名 - 主键
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键",
    )

    # 项目名称（从路径提取的友好名称）
    project_name = Column(
        String(255),
        nullable=False,
        comment="项目名称",
    )

    # 项目完整路径
    project_path = Column(
        Text,
        nullable=True,
        comment="项目完整路径",
    )

    # AI工具列表，以JSON格式存储
    ai_tools = Column(
        JSON,
        nullable=False,
        default=[],
        comment="AI工具列表，JSON格式存储",
    )

    # 首次执行时间
    first_active_at = Column(
        DateTime,
        nullable=True,
        comment="首次执行时间",
    )

    # 最后执行时间
    last_active_at = Column(
        DateTime,
        nullable=True,
        comment="最后执行时间",
    )

    # 创建时间
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )

    # 最后更新时间
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<AIProject(id={self.id}, name={self.project_name}, tools={self.ai_tools})>"
