"""Универсальный репозиторий с базовыми CRUD-операциями."""

from typing import Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDRepository(Generic[ModelT]):
    """Общие операции для простых справочников (бренды, категории, автомобили)."""

    def __init__(self, model: type[ModelT], name: str):
        self.model = model
        self.name = name  # человекочитаемое имя для сообщений об ошибках

    async def get_or_404(self, session: AsyncSession, obj_id: int) -> ModelT:
        obj = await session.get(self.model, obj_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{self.name} с id={obj_id} не найден(а)")
        return obj

    async def paginate(
        self, session: AsyncSession, query: Select, page: int, size: int
    ) -> tuple[list[ModelT], int]:
        """Возвращает элементы страницы и общее количество записей."""
        total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        result = await session.scalars(query.offset((page - 1) * size).limit(size))
        return list(result.unique().all()), total or 0

    async def create(self, session: AsyncSession, data: BaseModel) -> ModelT:
        obj = self.model(**data.model_dump())
        session.add(obj)
        await self.commit(session)
        await session.refresh(obj)
        return obj

    async def update(self, session: AsyncSession, obj: ModelT, data: BaseModel) -> ModelT:
        # exclude_unset — частичное обновление (PATCH): меняем только переданные поля
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        await self.commit(session)
        await session.refresh(obj)
        return obj

    async def delete(self, session: AsyncSession, obj: ModelT) -> None:
        await session.delete(obj)
        await self.commit(session)

    async def commit(self, session: AsyncSession) -> None:
        """Коммит с переводом ошибок целостности БД в HTTP 409."""
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{self.name}: нарушение уникальности или связанные данные",
            ) from exc
