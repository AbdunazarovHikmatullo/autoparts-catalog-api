"""Тесты справочников: бренды, категории, автомобили."""

from httpx import AsyncClient


async def test_brand_crud(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/brands", json={"name": "Brembo", "country": "Италия"}, headers=auth_headers)
    assert resp.status_code == 201
    brand_id = resp.json()["id"]

    assert (await client.get(f"/api/v1/brands/{brand_id}")).json()["name"] == "Brembo"

    resp = await client.patch(f"/api/v1/brands/{brand_id}", json={"country": "Italy"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["country"] == "Italy"
    assert resp.json()["name"] == "Brembo"

    assert (await client.delete(f"/api/v1/brands/{brand_id}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/v1/brands/{brand_id}")).status_code == 404


async def test_brand_unique_name(client: AsyncClient, auth_headers):
    await client.post("/api/v1/brands", json={"name": "NGK"}, headers=auth_headers)
    resp = await client.post("/api/v1/brands", json={"name": "NGK"}, headers=auth_headers)
    assert resp.status_code == 409


async def test_brand_search_and_pagination(client: AsyncClient, auth_headers):
    for name in ["Bosch", "Brembo", "Febi", "Lemforder", "Sachs"]:
        await client.post("/api/v1/brands", json={"name": name}, headers=auth_headers)

    page = (await client.get("/api/v1/brands", params={"page": 2, "size": 2})).json()
    assert page["total"] == 5
    assert page["pages"] == 3
    assert [b["name"] for b in page["items"]] == ["Febi", "Lemforder"]

    found = (await client.get("/api/v1/brands", params={"q": "br"})).json()
    assert [b["name"] for b in found["items"]] == ["Brembo"]


async def test_cannot_delete_brand_with_parts(client: AsyncClient, auth_headers, catalog):
    brand_id = catalog["brands"][0]["id"]
    resp = await client.delete(f"/api/v1/brands/{brand_id}", headers=auth_headers)
    assert resp.status_code == 409


async def test_category_crud_and_slug_validation(client: AsyncClient, auth_headers):
    bad = await client.post("/api/v1/categories", json={"name": "Подвеска", "slug": "Bad Slug"}, headers=auth_headers)
    assert bad.status_code == 422

    resp = await client.post("/api/v1/categories", json={"name": "Подвеска", "slug": "suspension"}, headers=auth_headers)
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/categories/{cat_id}", json={"description": "Амортизаторы"}, headers=auth_headers)
    assert resp.json()["description"] == "Амортизаторы"
    assert (await client.delete(f"/api/v1/categories/{cat_id}", headers=auth_headers)).status_code == 204


async def test_vehicle_year_validation_and_filter(client: AsyncClient, auth_headers):
    bad = await client.post(
        "/api/v1/vehicles", json={"make": "Kia", "model": "Rio", "year_from": 2020, "year_to": 2010}, headers=auth_headers
    )
    assert bad.status_code == 422

    resp = await client.post(
        "/api/v1/vehicles", json={"make": "Kia", "model": "Rio", "year_from": 2011, "year_to": 2017}, headers=auth_headers
    )
    vehicle_id = resp.json()["id"]

    assert (await client.get("/api/v1/vehicles", params={"year": 2015})).json()["total"] == 1
    assert (await client.get("/api/v1/vehicles", params={"year": 2019})).json()["total"] == 0

    bad_patch = await client.patch(f"/api/v1/vehicles/{vehicle_id}", json={"year_to": 2000}, headers=auth_headers)
    assert bad_patch.status_code == 422
