"""
应用设置CRUD操作
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..orms.app_setting import AppSetting
from ..schemas.app_setting import (
    AppSettingCreate,
    AppSettingInDB,
    AppSettingUpdate,
)
from .base_crud import CRUDBase


class AppSettingCRUD(
    CRUDBase[AppSetting, AppSettingCreate, AppSettingUpdate, AppSettingInDB]
):
    """应用设置CRUD操作类，继承CRUDBase基类"""

    async def check_key_exists(self, db: AsyncSession, *, key: str) -> bool:
        """
        检查键名是否已存在

        Args:
            db: 数据库会话
            key: 要检查的键名

        Returns:
            是否存在
        """
        count = await self.count(db, where=AppSetting.id == key)
        return count > 0

    async def upsert_by_key(
        self, db: AsyncSession, *, key: str, value: str
    ) -> AppSettingInDB:
        """
        根据键名插入或更新设置

        Args:
            db: 数据库会话
            key: 设置键名
            value: 设置值

        Returns:
            创建或更新后的设置
        """
        existing_setting = await self.get_by_id(db, id=key)

        if existing_setting:
            # 更新现有设置
            update_data = AppSettingUpdate(value=value)
            return await self.update(db, id=key, obj_update=update_data)
        else:
            # 创建新设置
            create_data = AppSettingCreate(id=key, value=value)
            return await self.create(db, obj_in=create_data)


# 创建全局实例
app_setting_crud = AppSettingCRUD(model=AppSetting, schema=AppSettingInDB)
