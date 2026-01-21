"""
AI项目CRUD操作
"""

from typing import List

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..orms.ai_project import AIProject
from ..schemas.ai_project import AIProjectCreate, AIProjectInDB, AIProjectUpdate
from .base_crud import CRUDBase


class AIProjectCRUD(
    CRUDBase[AIProject, AIProjectCreate, AIProjectUpdate, AIProjectInDB]
):
    """AI项目CRUD操作类"""

    async def read_by_path(
        self, db: AsyncSession, *, project_path: str
    ) -> AIProjectInDB:
        return await self.read_one(db, where=AIProject.project_path == project_path)

    async def remove_projects(self, db: AsyncSession, *, project_ids: List[int]) -> int:
        """
        批量标记项目为已移除（removed=True）

        Args:
            db: 数据库会话
            project_ids: 项目ID列表

        Returns:
            更新的记录数
        """
        query = (
            update(AIProject).where(AIProject.id.in_(project_ids)).values(removed=True)
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount


# 创建全局CRUD实例
ai_project_crud = AIProjectCRUD(model=AIProject, schema=AIProjectInDB)
