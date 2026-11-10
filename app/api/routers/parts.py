"""Запчасти: CRUD, полнотекстовый поиск, фильтры, сортировка и пагинация."""

from decimal import Decimal
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.crud.base import CRUDRepository
from app.models import Brand, Category, Part, Vehicle
from app.schemas.catalog import PartCreate, PartRead, PartUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/parts", tags=["Запчасти"])
repo = CRUDRepository(Part, "Запчасть")


class PartOrdering(str, Enum):
    """Допустимые варианты сортировки. Минус в начале — по убыванию."""

    name = "name"
    name_desc = "-name"
    price = "price"
    price_desc = "-price"
    newest = "-created_at"
    oldest = "created_at"


ORDERING_MAP = {
    PartOrdering.name: Part.name.asc(),
    PartOrdering.name_desc: Part.name.desc(),
    PartOrdering.price: Part.price.asc(),
    PartOrdering.price_desc: Part.price.desc(),
    PartOrdering.newest: Part.created_at.desc(),
    PartOrdering.oldest: Part.created_at.asc(),
}


async def _ensure_exists(session: AsyncSession, model, obj_id: int, label: str) -> None:
    """Проверяет, что связанный объект существует, иначе 422."""
    if await session.get(model, obj_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label} с id={obj_id} не существует")


async def _load_vehicles(session: AsyncSession, vehicle_ids: list[int]) -> list[Vehicle]:
    """Загружает автомобили по списку id и проверяет, что найдены все."""
    if not vehicle_ids:
        return []
    unique_ids = set(vehicle_ids)
    vehicles = list(await session.scalars(select(Vehicle).where(Vehicle.id.in_(unique_ids))))
    missing = unique_ids - {v.id for v in vehicles}
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Автомобили не найдены: {sorted(missing)}"
        )
    return vehicles


async def _reload(session: AsyncSession, part_id: int) -> Part:
    """Перечитывает запчасть вместе со связями после изменения."""
    stmt = select(Part).where(Part.id == part_id).execution_options(populate_existing=True)
    return (await session.scalars(stmt)).one()


@router.get("", response_model=Page[PartRead])
async def list_parts(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(description="Поиск по названию, артикулу и описанию")] = None,
    brand_id: Annotated[list[int] | None, Query(description="Один или несколько брендов")] = None,
    category_id: int | None = None,
    vehicle_id: Annotated[int | None, Query(description="Только совместимые с автомобилем")] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    in_stock: Annotated[bool | None, Query(description="true — только в наличии")] = None,
    ordering: PartOrdering = PartOrdering.name,
):
    """Список запчастей с поиском и фильтрами. Все фильтры комбинируются через AND."""
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "min_price больше max_price")

    query = select(Part)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(Part.name.ilike(pattern), Part.sku.ilike(pattern), Part.description.ilike(pattern))
        )
    if brand_id:
        query = query.where(Part.brand_id.in_(brand_id))
    if category_id is not None:
        query = query.where(Part.category_id == category_id)
    if vehicle_id is not None:
        query = query.where(Part.vehicles.any(Vehicle.id == vehicle_id))
    if min_price is not None:
        query = query.where(Part.price >= min_price)
    if max_price is not None:
        query = query.where(Part.price <= max_price)
    if in_stock is True:
        query = query.where(Part.quantity > 0)
    elif in_stock is False:
        query = query.where(Part.quantity == 0)

    # Вторичная сортировка по id делает пагинацию стабильной
    query = query.order_by(ORDERING_MAP[ordering], Part.id)
    items, total = await repo.paginate(session, query, pagination.page, pagination.size)
    return Page.create(items, total, pagination.page, pagination.size)


@router.get("/{part_id}", response_model=PartRead)
async def get_part(part_id: int, session: SessionDep):
    return await repo.get_or_404(session, part_id)


@router.post("", response_model=PartRead, status_code=status.HTTP_201_CREATED)
async def create_part(data: PartCreate, session: SessionDep, _: CurrentUser):
    await _ensure_exists(session, Brand, data.brand_id, "Бренд")
    await _ensure_exists(session, Category, data.category_id, "Категория")
    vehicles = await _load_vehicles(session, data.vehicle_ids)

    part = Part(**data.model_dump(exclude={"vehicle_ids"}), vehicles=vehicles)
    session.add(part)
    await repo.commit(session)
    return await _reload(session, part.id)


@router.patch("/{part_id}", response_model=PartRead)
async def update_part(part_id: int, data: PartUpdate, session: SessionDep, _: CurrentUser):
    part = await repo.get_or_404(session, part_id)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("brand_id") is not None:
        await _ensure_exists(session, Brand, changes["brand_id"], "Бренд")
    if changes.get("category_id") is not None:
        await _ensure_exists(session, Category, changes["category_id"], "Категория")
    if "vehicle_ids" in changes:
        part.vehicles = await _load_vehicles(session, changes.pop("vehicle_ids") or [])

    for field, value in changes.items():
        if value is None and field in {"sku", "name", "price", "quantity", "brand_id", "category_id"}:
            continue  # обязательные поля нельзя обнулить
        setattr(part, field, value)
    await repo.commit(session)
    return await _reload(session, part.id)


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part(part_id: int, session: SessionDep, _: CurrentUser) -> None:
    part = await repo.get_or_404(session, part_id)
    await repo.delete(session, part)
