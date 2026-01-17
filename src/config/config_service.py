"""
配置管理服务
提供配置的加载和更新功能
"""

from typing import List, Optional

from ..database.connection import get_db
from ..database.cruds.app_setting_crud import app_setting_crud
from ..database.schemas.app_setting import AppSettingInDB
from .config_change_listener import ConfigKeyUpdateEvent, config_change_manager


class ConfigService:
    """配置管理服务类"""

    async def initialize(self):
        """
        初始化配置服务
        触发配置初始化事件
        """
        from .config_change_listener import ConfigInitializeEvent, config_change_manager

        # 创建初始化事件
        event = ConfigInitializeEvent(results={})

        # 通知所有监听器进行初始化
        await config_change_manager.notify_initialize(event)

    async def get_setting(self, key: str) -> Optional[str]:
        """
        获取配置值

        Args:
            key: 配置键名

        Returns:
            配置值或None
        """
        async with get_db() as db:
            setting = await app_setting_crud.get_by_id(db, id=key)
            return setting.value if setting else None

    async def set_setting(self, key: str, value: str) -> AppSettingInDB:
        """
        设置配置值

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            更新后的配置对象

        Raises:
            ValueError: 如果配置校验失败
        """
        async with get_db() as db:
            # 检查是否已存在配置
            existing_setting = await app_setting_crud.get_by_id(db, id=key)
            old_value = existing_setting.value if existing_setting else None

            # 如果值没有变化，直接返回现有配置
            if old_value == value:
                return (
                    existing_setting
                    if existing_setting
                    else AppSettingInDB(id=key, value=value, updated_at=None)
                )

            # 先进行配置校验
            validation_event = ConfigKeyUpdateEvent(
                key=key, old_value=old_value, new_value=value
            )

            validation_result = await config_change_manager.before_key_update(
                validation_event
            )
            if not validation_result.success:
                raise ValueError(f"配置校验失败: {validation_result.error_message}")

            # 创建事件用于后续通知
            event = ConfigKeyUpdateEvent(key=key, old_value=old_value, new_value=value)

            # 执行更新或新增
            updated_setting = await app_setting_crud.upsert_by_key(
                db, key=key, value=value
            )

            # 触发配置键更新事件
            await config_change_manager.notify_key_updated(event)
            return updated_setting

    async def get_all_settings(self) -> List[AppSettingInDB]:
        """
        获取所有配置

        Returns:
            所有配置列表
        """
        async with get_db() as db:
            return await app_setting_crud.read_all(db)


# 创建全局配置服务实例
config_service = ConfigService()
