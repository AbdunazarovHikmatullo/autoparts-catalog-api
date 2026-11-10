"""CRUD для брендов. Чтение — публичное, изменение — только для авторизованных."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.crud.base import CRUDRepository
from app.models import Brand, Part
from app.schemas.catalog import BrandCreate, BrandRead, BrandUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/brands", tags=["Бренды"])
repo = CRUDRepository(Brand, "Бренд")


@router.get("", response_model=Page[BrandRead])
async def list_brands(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(description="Поиск по названию")] = None,
    country: str | None = None,
):
    query = select(Brand).order_by(Brand.name)
    if q:
        query = query.where(Brand.name.ilike(f"%{q}%"))
    if country:
        query = query.where(Brand.country.ilike(country))
    items, total = await repo.paginate(session, query, pagination.page, pagination.size)
    return Page.create(items, total, pagination.page, pagination.size)


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(brand_id: int, session: SessionDep):
    return await repo.get_or_404(session, brand_id)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(data: BrandCreate, session: SessionDep, _: CurrentUser):
    return await repo.create(session, data)


@router.patch("/{brand_id}", response_model=BrandRead)
async def update_brand(brand_id: int, data: BrandUpdate, session: SessionDep, _: CurrentUser):
    brand = await repo.get_or_404(session, brand_id)
    return await repo.update(session, brand, data)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(brand_id: int, session: SessionDep, _: CurrentUser) -> None:
    """Удалить бренд нельзя, если к нему привязаны запчасти (вернётся 409)."""
    brand = await repo.get_or_404(session, brand_id)
    linked = await session.scalar(select(func.count(Part.id)).where(Part.brand_id == brand_id))
    if linked:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Нельзя удалить: привязано запчастей — {linked}")
    await repo.delete(session, brand)
