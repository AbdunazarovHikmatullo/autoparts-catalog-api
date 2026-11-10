"""CRUD для категорий запчастей. Удалить категорию с запчастями нельзя (409)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.crud.base import CRUDRepository
from app.models import Category, Part
from app.schemas.catalog import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/categories", tags=["Категории"])
repo = CRUDRepository(Category, "Категория")


@router.get("", response_model=Page[CategoryRead])
async def list_categories(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(description="Поиск по названию")] = None,
):
    query = select(Category).order_by(Category.name)
    if q:
        query = query.where(Category.name.ilike(f"%{q}%"))
    items, total = await repo.paginate(session, query, pagination.page, pagination.size)
    return Page.create(items, total, pagination.page, pagination.size)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, session: SessionDep):
    return await repo.get_or_404(session, category_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, session: SessionDep, _: CurrentUser):
    return await repo.create(session, data)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(category_id: int, data: CategoryUpdate, session: SessionDep, _: CurrentUser):
    category = await repo.get_or_404(session, category_id)
    return await repo.update(session, category, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, session: SessionDep, _: CurrentUser) -> None:
    category = await repo.get_or_404(session, category_id)
    linked = await session.scalar(select(func.count(Part.id)).where(Part.category_id == category_id))
    if linked:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Нельзя удалить: привязано запчастей — {linked}")
    await repo.delete(session, category)
