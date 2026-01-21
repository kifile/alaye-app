"""
AI项目会话CRUD操作
"""

from typing import Any, List, Optional

from sqlalchemy import and_, or_, update
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
    """AI项目会话CRUD操作类，支持软删除"""

    def _add_soft_delete_filter(
        self, where_conditions: List, include_removed: bool = False
    ) -> List:
        """添加软删除过滤条件

        Args:
            where_conditions: 现有的查询条件列表
            include_removed: 是否包含已删除的记录
        """
        if not include_removed:
            where_conditions.append(
                or_(self.model.removed == False, self.model.removed == None)
            )
        return where_conditions

    async def get_by_project_session(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        session_id: str,
        include_removed: bool = False,
    ) -> Optional[AIProjectSessionInDB]:
        """
        根据会话ID和项目ID获取会话

        Args:
            db: 数据库会话
            session_id: 会话ID
            project_id: 项目ID
            include_removed: 是否包含已删除的记录

        Returns:
            会话信息，如果不存在则返回None
        """
        where_conditions = [
            AIProjectSession.session_id == session_id,
            AIProjectSession.project_id == project_id,
        ]
        where_conditions = self._add_soft_delete_filter(
            where_conditions, include_removed
        )

        return await self.read_one(db, where=and_(*where_conditions))

    async def get_by_project_id(
        self,
        db: AsyncSession,
        *,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
        is_agent_session: Optional[bool] = None,
        include_removed: bool = False,
    ) -> List[AIProjectSessionInDB]:
        """
        根据项目ID获取会话列表

        Args:
            db: 数据库会话
            project_id: 项目ID
            skip: 跳过的记录数
            limit: 返回的记录数限制
            is_agent_session: 是否为Agent会话过滤条件
            include_removed: 是否包含已删除的记录

        Returns:
            会话列表
        """
        where_conditions = [self.model.project_id == project_id]
        where_conditions = self._add_soft_delete_filter(
            where_conditions, include_removed
        )

        if is_agent_session is not None:
            where_conditions.append(self.model.is_agent_session == is_agent_session)

        return await self.read_all(
            db,
            where=and_(*where_conditions),
            order_by=self.model.updated_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def delete(
        self, db: AsyncSession, *, id: str, where: Any = None
    ) -> Optional[AIProjectSessionInDB]:
        """
        软删除会话（标记为已删除）

        Args:
            db: 数据库会话
            id: 会话ID

        Returns:
            被删除的会话信息，如果不存在则返回None
        """
        # 先获取会话信息
        db_obj = await self._read_by_id(db, id=id, where=where)
        if not db_obj:
            return None

        # 软删除：更新 removed 标记
        stmt = update(self.model).where(self.model.id == id).values(removed=True)
        if where is not None:
            stmt = stmt.where(where)

        await db.execute(stmt)
        await db.commit()
        await db.refresh(db_obj)

        return self.schema.model_validate(db_obj)

    async def delete_by_project_id(self, db: AsyncSession, *, project_id: int) -> int:
        """
        根据项目ID软删除所有相关会话

        Args:
            db: 数据库会话
            project_id: 项目ID

        Returns:
            更新的记录数
        """
        stmt = (
            update(self.model)
            .where(self.model.project_id == project_id)
            .values(removed=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def hard_delete(
        self, db: AsyncSession, *, id: str
    ) -> Optional[AIProjectSessionInDB]:
        """
        硬删除会话（真正从数据库中删除）

        Args:
            db: 数据库会话
            id: 会话ID

        Returns:
            被删除的会话信息，如果不存在则返回None
        """
        return await super().delete(db, id=id)

    async def restore(
        self, db: AsyncSession, *, id: str
    ) -> Optional[AIProjectSessionInDB]:
        """
        恢复已删除的会话

        Args:
            db: 数据库会话
            id: 会话ID

        Returns:
            恢复的会话信息，如果不存在则返回None
        """
        db_obj = await self._read_by_id(db, id=id)
        if not db_obj:
            return None

        stmt = update(self.model).where(self.model.id == id).values(removed=False)
        await db.execute(stmt)
        await db.commit()
        await db.refresh(db_obj)

        return self.schema.model_validate(db_obj)


# 创建全局CRUD实例
ai_project_session_crud = AIProjectSessionCRUD(
    model=AIProjectSession, schema=AIProjectSessionInDB
)
