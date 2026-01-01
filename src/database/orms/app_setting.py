"""
应用设置ORM模型
"""

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from .base import Base


class AppSetting(Base):
    """
    应用设置模型

    存储应用的各种配置信息，包括工具路径、版本信息等
    """

    __tablename__ = "app_settings"

    # 设置键名 - 主键
    id = Column(
        String(255),
        primary_key=True,
        nullable=False,
        comment="设置键名，主键",
    )

    # 设置值
    value = Column(Text, nullable=True, comment="设置值")

    # 最后更新时间
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    def __repr__(self):
        return f"<AppSetting(id={self.id}, value={self.value})>"
