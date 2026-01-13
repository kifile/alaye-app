"""
AI项目会话CRUD操作
"""

from typing import List, Optional

from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..orms.ai_project_session import AIProjectSession
from ..schemas.ai_project_session import (
    AIProjectSessionCreate,
    AIProjectSessionInDB,
    AIProjectSessionUpdate,
)
from .base_crud import CRUDBase


class AIProjectSessionCRUD(
    CRUDBase[
        AIProjectSession,
        AIProjectSessionCreate,
        AIProjectSessionUpdate,
        AIProjectSessionInDB,
    ]
):
    """AI项目会话CRUD操作类"""

    async def get_by_project_session(
        self, db: AsyncSession, *, project_id: str, session_id: str
    ) -> Optional[AIProjectSessionInDB]:
        """
        根据会话ID和项目ID获取会话

        Args:
            db: 数据库会话
            session_id: 会话ID
            project_id: 项目ID

        Returns:
            会话信息，如果不存在则返回None
        """
        return await self.read_one(
            db,
            where=and_(
                AIProjectSession.session_id == session_id,
                AIProjectSession.project_id == project_id,
            ),
        )

    async def get_by_project_id(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        skip: int = 0,
        limit: int = 100,
        is_agent_session: Optional[bool] = None,
    ) -> List[AIProjectSessionInDB]:
        """
        根据项目ID获取会话列表

        Args:
            db: 数据库会话
            project_id: 项目ID
            skip: 跳过的记录数
            limit: 返回的记录数限制
            is_agent_session: 是否为Agent会话过滤条件

        Returns:
            会话列表
        """
        where_conditions = [self.model.project_id == project_id]

        if is_agent_session is not None:
            where_conditions.append(self.model.is_agent_session == is_agent_session)

        return await self.read_all(
            db,
            where=and_(*where_conditions),
            order_by=self.model.updated_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def delete_by_project_id(self, db: AsyncSession, *, project_id: str) -> int:
        """
        根据项目ID删除所有相关会话

        Args:
            db: 数据库会话
            project_id: 项目ID

        Returns:
            删除的记录数
        """

        stmt = delete(self.model).where(self.model.project_id == project_id)
        result = await db.execute(stmt)
        return result.rowcount


# 创建全局CRUD实例
ai_project_session_crud = AIProjectSessionCRUD(
    model=AIProjectSession, schema=AIProjectSessionInDB
)
