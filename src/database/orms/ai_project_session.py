"""
AI项目会话ORM模型
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .base import Base


class AIProjectSession(Base):
    """
    AI项目会话模型

    存储 Claude 项目中的会话信息
    """

    __tablename__ = "ai_project_sessions"

    # 自增主键
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键",
    )

    # 会话ID
    session_id = Column(
        String(255),
        nullable=False,
        comment="会话ID",
    )

    # 关联的项目ID（业务关联，无外键约束）
    project_id = Column(
        Integer,
        nullable=False,
        index=True,  # 添加索引以提高查询性能
        comment="关联的项目ID",
    )

    # 会话文件路径
    session_file = Column(
        Text,
        nullable=True,
        comment="会话文件路径",
    )

    # 会话文件MD5哈希值（用于检测文件变化）
    session_file_md5 = Column(
        String(32),
        nullable=True,
        comment="会话文件MD5哈希值",
    )

    # 是否为Agent会话
    is_agent_session = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否为Agent会话",
    )

    # AI工具类型
    ai_tool = Column(
        String(50),
        nullable=False,
        default="",
        comment="AI工具类型",
    )

    # 项目路径（从会话中提取）
    project_path = Column(
        Text,
        nullable=True,
        comment="项目路径",
    )

    # Git分支
    git_branch = Column(
        String(255),
        nullable=True,
        comment="Git分支",
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
        return f"<AIProjectSession(session_id={self.session_id}, project_id={self.project_id}, tool={self.ai_tool}, agent={self.is_agent_session})>"
