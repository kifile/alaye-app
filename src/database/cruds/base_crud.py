"""
Base CRUD operations
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..base.common import PagedData

# Define generic types for SQLAlchemy model and Pydantic schemas
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
InDbSchemaType = TypeVar("InDbSchemaType", bound=BaseModel)


class CRUDException(Exception):
    """Base exception for CRUD operations."""


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType, InDbSchemaType]):
    """
    Base class for CRUD operations.

    Provides standard create, read, update, delete operations.
    """

    def __init__(self, model: Type[ModelType], schema: Type[InDbSchemaType]):
        """
        Initialize with the SQLAlchemy model class and Pydantic schema.
        Args:
            model: The SQLAlchemy model class
            schema: The Pydantic schema class
        """
        self.model = model
        self.schema = schema
        self._model_attrs = self.model.__table__.columns.keys()

    async def _create(
        self, db: AsyncSession, *, dict_create: Dict[str, Any]
    ) -> ModelType:
        """
        Create a new record.
        Args:
            db: Database session
            dict_create: Pydantic schema with create data
        Returns:
            The created model instance
        """
        db_obj = self.model(**dict_create)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def _read_by_id(
        self, db: AsyncSession, *, id: Any, where: Any = None
    ) -> Optional[ModelType]:
        """
        Read a record by id with optional where condition.
        Args:
            db: Database session
            id: ID of the record
            where: Optional SQLAlchemy where clause for additional filtering
        Returns:
            The model instance if found, otherwise None
        """
        id_where = self.model.id == id
        if where is not None:
            id_where = and_(id_where, where)
        return await self._read_one(db, where=id_where)

    async def _read_one(
        self, db: AsyncSession, *, where: Any = None, order_by: Any = None
    ) -> Optional[ModelType]:
        """
        Read a single record with optional filtering and ordering.
        Args:
            db: Database session
            where: Optional SQLAlchemy where clause for filtering
            order_by: Optional SQLAlchemy order_by clause for sorting
        Returns:
            The model instance if found, otherwise None
        """
        query = select(self.model)
        if where is not None:
            query = query.where(where)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.limit(1)
        result = await db.execute(query)
        return result.scalars().first()

    async def _read_all(
        self,
        db: AsyncSession,
        where: Any,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[Any] = None,
    ) -> List[ModelType]:
        """
        Read all records.
        Args:
            db: Database session
        Returns:
            List of model instances
        """
        query = select(self.model)
        if where is not None:
            query = query.where(where)
        if skip is not None:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        if order_by is not None:
            if isinstance(order_by, list):
                # If order_by is a list, unpack it when passing to order_by()
                query = query.order_by(*order_by)
            else:
                query = query.order_by(order_by)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def _update(
        self, db: AsyncSession, *, db_obj: ModelType, dict_update: Dict[str, Any]
    ) -> ModelType:
        """
        Update a record.
        Args:
            db: Database session
            db_obj: Existing database object
            dict_update: Update data
        Returns:
            The updated model instance
        """
        # Update object attributes directly
        for key, value in dict_update.items():
            setattr(db_obj, key, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def _count(self, db: AsyncSession, where: Any) -> int:
        """
        Count total number of records.
        Args:
            db: Database session
        Returns:
            Total count of records
        """
        query = select(func.count()).select_from(self.model)
        if where is not None:
            query = query.where(where)
        result = await db.execute(query)
        return result.scalar() or 0

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType
    ) -> InDbSchemaType:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Pydantic schema with create data

        Returns:
            The created model instance
        """
        # Convert to dict if it's a Pydantic model
        dict_create = obj_in.model_dump(exclude_none=True, include=self._model_attrs)

        db_obj = await self._create(db, dict_create=dict_create)
        return self.schema.model_validate(db_obj)

    async def get_by_id(
        self, db: AsyncSession, id: Any, where: Any = None
    ) -> Optional[InDbSchemaType]:
        """
        Get a record by id.

        Args:
            db: Database session
            id: ID of the record (string UUID)

        Returns:
            The model instance if found, otherwise None
        """
        result = await self._read_by_id(db, id=id, where=where)
        return self.schema.model_validate(result) if result else None

    async def read_one(
        self, db: AsyncSession, where: Any = None, order_by: Any = None
    ) -> Optional[InDbSchemaType]:
        """
        Get a record by id.

        Args:
            db: Database session
            id: ID of the record (string UUID)

        Returns:
            The model instance if found, otherwise None
        """
        result = await self._read_one(db, where=where, order_by=order_by)
        return self.schema.model_validate(result) if result else None

    async def read_all(
        self, db: AsyncSession, *, where: Any = None, order_by: Any = None, skip: int = None, limit: int = None
    ) -> List[InDbSchemaType]:
        result = await self._read_all(db, where=where, order_by=order_by, skip=skip, limit=limit)
        return [self.schema.model_validate(item) for item in result]

    async def update(
        self,
        db: AsyncSession,
        *,
        id: Any,
        obj_update: UpdateSchemaType,
        where: Any = None,
    ) -> InDbSchemaType:
        """
        Update a record.

        Args:
            db: Database session
            db_obj: Existing database object
            obj_update: Update data (schema or dict)

        Returns:
            The updated model instance
        """
        db_obj = await self._read_by_id(db, id=id, where=where)
        if not db_obj:
            raise CRUDException(f"Object with id {id} not found")

        # Convert to dict if it's a Pydantic model
        dict_update = obj_update.model_dump(
            exclude_none=True, include=self._model_attrs
        )

        db_obj = await self._update(db, db_obj=db_obj, dict_update=dict_update)
        return self.schema.model_validate(db_obj)

    async def delete(
        self, db: AsyncSession, *, id: str, where: Any = None
    ) -> Optional[InDbSchemaType]:
        """
        Delete a record.

        Args:
            db: Database session
            id: ID of the record to delete (string UUID)

        Returns:
            True if deleted, False if not found
        """
        # First check if the object exists
        db_obj = await self._read_by_id(db, id=id, where=where)
        if not db_obj:
            return None

        # Delete the object
        await db.delete(db_obj)
        await db.commit()
        return self.schema.model_validate(db_obj)

    async def delete_all(self, db: AsyncSession, *, where: Any):
        """Delete all records matching the where condition.

        Args:
            db: Database session
            where: SQLAlchemy where clause for filtering records to delete
        """
        # Execute delete query with where condition
        query = delete(self.model)
        if where is not None:
            query = query.where(where)
        await db.execute(query)
        await db.commit()

    async def count(self, db: AsyncSession, where: Any = None) -> int:
        """
        Count total number of records.
        Args:
            db: Database session
        Returns:
            Total count of records
        """
        return await self._count(db, where=where)

    async def read_page_result(
        self,
        db: AsyncSession,
        *,
        page_num: int = 1,
        page_size: int = 10,
        where: Any = None,
        order_by: Any = None,
    ) -> PagedData[InDbSchemaType]:
        """
        Get multiple records with optional filtering and pagination.

        Args:
            db: Database session
            page_num: Page number (default: 1)
            page_size: Number of items per page (default: 10)
            where: SQLAlchemy where clause

        Returns:
            List of model instances
        """
        if page_size == -1:
            items = await self._read_all(
                db,
                where,
                order_by=order_by if order_by is not None else self.model.id.desc(),
            )
            return PagedData(
                items=[self.schema.model_validate(item) for item in items],
                total=len(items),
                page=page_num,
                size=page_size,
                pages=1,
            )
        count = await self._count(db, where)
        items = await self._read_all(
            db,
            where,
            skip=(page_num - 1) * page_size,
            limit=page_size,
            order_by=order_by if order_by is not None else self.model.id.desc(),
        )
        return PagedData(
            items=[self.schema.model_validate(item) for item in items],
            total=count,
            page=page_num,
            size=page_size,
            pages=(count + page_size - 1) // page_size,
        )
