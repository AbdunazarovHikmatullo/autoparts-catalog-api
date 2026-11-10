"""Общие фикстуры: отдельная SQLite-база на каждый тест и HTTP-клиент."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


@pytest.fixture
async def session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    # В SQLite внешние ключи по умолчанию выключены — включаем
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Регистрирует пользователя и возвращает заголовок с JWT."""
    await client.post(
        "/api/v1/auth/register", json={"email": "user@example.com", "password": "strongpass123"}
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "user@example.com", "password": "strongpass123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def catalog(client: AsyncClient, auth_headers) -> dict:
    """Наполняет каталог тестовыми данными: 2 бренда, 2 категории, 2 авто, 4 запчасти."""
    h = auth_headers
    bosch = (await client.post("/api/v1/brands", json={"name": "Bosch", "country": "Германия"}, headers=h)).json()
    mann = (await client.post("/api/v1/brands", json={"name": "Mann-Filter", "country": "Германия"}, headers=h)).json()
    brakes = (await client.post("/api/v1/categories", json={"name": "Тормоза", "slug": "brakes"}, headers=h)).json()
    filters = (await client.post("/api/v1/categories", json={"name": "Фильтры", "slug": "filters"}, headers=h)).json()
    camry = (
        await client.post(
            "/api/v1/vehicles",
            json={"make": "Toyota", "model": "Camry", "year_from": 2017, "year_to": 2023},
            headers=h,
        )
    ).json()
    solaris = (
        await client.post(
            "/api/v1/vehicles",
            json={"make": "Hyundai", "model": "Solaris", "year_from": 2014, "year_to": 2020},
            headers=h,
        )
    ).json()

    parts_data = [
        {"sku": "BP-001", "name": "Тормозные колодки передние", "price": "3490.00", "quantity": 10,
         "brand_id": bosch["id"], "category_id": brakes["id"], "vehicle_ids": [camry["id"]]},
        {"sku": "BD-002", "name": "Тормозной диск", "price": "5200.50", "quantity": 0,
         "brand_id": bosch["id"], "category_id": brakes["id"], "vehicle_ids": [camry["id"], solaris["id"]]},
        {"sku": "OF-003", "name": "Масляный фильтр", "price": "690.00", "quantity": 25,
         "brand_id": mann["id"], "category_id": filters["id"], "vehicle_ids": [solaris["id"]]},
        {"sku": "AF-004", "name": "Воздушный фильтр", "price": "1150.00", "quantity": 3,
         "brand_id": mann["id"], "category_id": filters["id"], "description": "Фильтр салона и двигателя"},
    ]
    parts = []
    for data in parts_data:
        resp = await client.post("/api/v1/parts", json=data, headers=h)
        assert resp.status_code == 201, resp.text
        parts.append(resp.json())
    return {"brands": [bosch, mann], "categories": [brakes, filters], "vehicles": [camry, solaris], "parts": parts}
