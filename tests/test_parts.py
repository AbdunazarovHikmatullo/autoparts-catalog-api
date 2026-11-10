"""Тесты запчастей: CRUD, поиск, фильтры, сортировка, совместимость."""

import pytest
from httpx import AsyncClient


async def test_part_detail_contains_relations(client: AsyncClient, catalog):
    part = catalog["parts"][1]
    resp = await client.get(f"/api/v1/parts/{part['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand"]["name"] == "Bosch"
    assert body["category"]["slug"] == "brakes"
    assert len(body["vehicles"]) == 2
    assert body["price"] == 5200.5
    assert body["in_stock"] is False


async def test_create_part_with_unknown_brand(client: AsyncClient, auth_headers, catalog):
    payload = {"sku": "X-1", "name": "Свеча", "price": "100", "brand_id": 999,
               "category_id": catalog["categories"][0]["id"]}
    resp = await client.post("/api/v1/parts", json=payload, headers=auth_headers)
    assert resp.status_code == 422


async def test_create_part_duplicate_sku(client: AsyncClient, auth_headers, catalog):
    payload = {"sku": "BP-001", "name": "Дубль", "price": "1", "brand_id": catalog["brands"][0]["id"],
               "category_id": catalog["categories"][0]["id"]}
    resp = await client.post("/api/v1/parts", json=payload, headers=auth_headers)
    assert resp.status_code == 409


async def test_negative_price_rejected(client: AsyncClient, auth_headers, catalog):
    payload = {"sku": "NEG", "name": "Ошибка", "price": "-5", "brand_id": catalog["brands"][0]["id"],
               "category_id": catalog["categories"][0]["id"]}
    assert (await client.post("/api/v1/parts", json=payload, headers=auth_headers)).status_code == 422


async def test_update_and_delete_part(client: AsyncClient, auth_headers, catalog):
    part_id = catalog["parts"][0]["id"]
    solaris_id = catalog["vehicles"][1]["id"]
    resp = await client.patch(
        f"/api/v1/parts/{part_id}",
        json={"price": "2990.00", "quantity": 0, "vehicle_ids": [solaris_id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 2990.0
    assert body["in_stock"] is False
    assert [v["id"] for v in body["vehicles"]] == [solaris_id]

    assert (await client.delete(f"/api/v1/parts/{part_id}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/v1/parts/{part_id}")).status_code == 404


async def test_update_part_requires_auth(client: AsyncClient, catalog):
    part_id = catalog["parts"][0]["id"]
    assert (await client.patch(f"/api/v1/parts/{part_id}", json={"quantity": 1})).status_code == 401


@pytest.mark.parametrize(
    ("params", "expected_skus"),
    [
        ({"q": "фильтр"}, {"OF-003", "AF-004"}),
        ({"q": "bd-002"}, {"BD-002"}),
        ({"q": "салона"}, {"AF-004"}),
        ({"in_stock": "true"}, {"BP-001", "OF-003", "AF-004"}),
        ({"in_stock": "false"}, {"BD-002"}),
        ({"min_price": "1000", "max_price": "4000"}, {"BP-001", "AF-004"}),
        ({"category_id": "__brakes__"}, {"BP-001", "BD-002"}),
        ({"brand_id": "__mann__"}, {"OF-003", "AF-004"}),
        ({"vehicle_id": "__camry__"}, {"BP-001", "BD-002"}),
        ({"vehicle_id": "__solaris__", "in_stock": "true"}, {"OF-003"}),
    ],
)
async def test_part_filters(client: AsyncClient, catalog, params, expected_skus):
    # Подставляем реальные id вместо плейсхолдеров
    ids = {
        "__brakes__": catalog["categories"][0]["id"],
        "__mann__": catalog["brands"][1]["id"],
        "__camry__": catalog["vehicles"][0]["id"],
        "__solaris__": catalog["vehicles"][1]["id"],
    }
    params = {k: ids.get(v, v) for k, v in params.items()}
    resp = await client.get("/api/v1/parts", params=params)
    assert resp.status_code == 200
    assert {p["sku"] for p in resp.json()["items"]} == expected_skus


async def test_multiple_brands_filter(client: AsyncClient, catalog):
    brand_ids = [b["id"] for b in catalog["brands"]]
    resp = await client.get("/api/v1/parts", params=[("brand_id", brand_ids[0]), ("brand_id", brand_ids[1])])
    assert resp.json()["total"] == 4


async def test_ordering_and_pagination(client: AsyncClient, catalog):
    resp = await client.get("/api/v1/parts", params={"ordering": "-price", "size": 2})
    body = resp.json()
    assert body["total"] == 4
    assert body["pages"] == 2
    assert [p["sku"] for p in body["items"]] == ["BD-002", "BP-001"]

    page2 = (await client.get("/api/v1/parts", params={"ordering": "-price", "size": 2, "page": 2})).json()
    assert [p["sku"] for p in page2["items"]] == ["AF-004", "OF-003"]


async def test_invalid_price_range(client: AsyncClient, catalog):
    resp = await client.get("/api/v1/parts", params={"min_price": "500", "max_price": "100"})
    assert resp.status_code == 422


async def test_page_size_limit(client: AsyncClient):
    assert (await client.get("/api/v1/parts", params={"size": 500})).status_code == 422
