"""Тесты регистрации, входа и защиты эндпоинтов."""

from httpx import AsyncClient


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_register_and_login(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "New@Example.com", "password": "password123", "full_name": "Иван"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "hashed_password" not in body

    resp = await client.post(
        "/api/v1/auth/login", data={"username": "new@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Иван"


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409


async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "123"})
    assert resp.status_code == 422


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", data={"username": "b@example.com", "password": "wrong-pass"})
    assert resp.status_code == 401


async def test_invalid_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401


async def test_write_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/brands", json={"name": "NoAuth"})
    assert resp.status_code == 401
