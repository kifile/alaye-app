"""
AI项目CRUD操作
"""

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


# 创建全局CRUD实例
ai_project_crud = AIProjectCRUD(model=AIProject, schema=AIProjectInDB)
