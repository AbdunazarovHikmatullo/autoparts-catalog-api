"""CRUD для автомобилей (используются для совместимости запчастей)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.crud.base import CRUDRepository
from app.models import Vehicle
from app.schemas.catalog import VehicleCreate, VehicleRead, VehicleUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/vehicles", tags=["Автомобили"])
repo = CRUDRepository(Vehicle, "Автомобиль")


@router.get("", response_model=Page[VehicleRead])
async def list_vehicles(
    session: SessionDep,
    pagination: PaginationDep,
    make: Annotated[str | None, Query(description="Марка, например Toyota")] = None,
    model: Annotated[str | None, Query(description="Модель, например Camry")] = None,
    year: Annotated[int | None, Query(description="Год выпуска автомобиля")] = None,
):
    query = select(Vehicle).order_by(Vehicle.make, Vehicle.model, Vehicle.year_from)
    if make:
        query = query.where(Vehicle.make.ilike(make))
    if model:
        query = query.where(Vehicle.model.ilike(f"%{model}%"))
    if year:
        query = query.where(Vehicle.year_from <= year, Vehicle.year_to >= year)
    items, total = await repo.paginate(session, query, pagination.page, pagination.size)
    return Page.create(items, total, pagination.page, pagination.size)


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(vehicle_id: int, session: SessionDep):
    return await repo.get_or_404(session, vehicle_id)


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(data: VehicleCreate, session: SessionDep, _: CurrentUser):
    return await repo.create(session, data)


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(vehicle_id: int, data: VehicleUpdate, session: SessionDep, _: CurrentUser):
    vehicle = await repo.get_or_404(session, vehicle_id)
    # Проверяем диапазон лет с учётом уже сохранённых значений
    year_from = data.year_from if data.year_from is not None else vehicle.year_from
    year_to = data.year_to if data.year_to is not None else vehicle.year_to
    if year_from > year_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "year_from не может быть больше year_to")
    return await repo.update(session, vehicle, data)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(vehicle_id: int, session: SessionDep, _: CurrentUser) -> None:
    vehicle = await repo.get_or_404(session, vehicle_id)
    await repo.delete(session, vehicle)
