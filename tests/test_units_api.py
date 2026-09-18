import pytest


@pytest.mark.asyncio
async def test_list_units_returns_seeded_units(client):
    response = await client.get("/units")
    assert response.status_code == 200
    units = response.json()
    symbols = {u["symbol"] for u in units}
    assert {"kg", "m", "s", "km", "cm", "°C"} <= symbols


@pytest.mark.asyncio
async def test_convert_km_to_m(client):
    response = await client.post(
        "/units/convert",
        json={"value": "5", "from_symbol": "km", "to_symbol": "m"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["value"] == "5000"
    assert body["unit"] == "m"
    assert body["input_value"] == "5"
    assert body["input_unit"] == "km"


@pytest.mark.asyncio
async def test_convert_celsius_to_kelvin(client):
    response = await client.post(
        "/units/convert",
        json={"value": "0", "from_symbol": "°C", "to_symbol": "K"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "273.15"


@pytest.mark.asyncio
async def test_convert_unknown_unit_returns_404(client):
    response = await client.post(
        "/units/convert",
        json={"value": "1", "from_symbol": "zzz", "to_symbol": "m"},
    )
    assert response.status_code == 404
    assert "zzz" in response.json()["detail"]


@pytest.mark.asyncio
async def test_convert_incompatible_units_returns_422(client):
    response = await client.post(
        "/units/convert",
        json={"value": "1", "from_symbol": "kg", "to_symbol": "m"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "kg" in detail and "m" in detail


@pytest.mark.asyncio
async def test_check_compatibility_km_m(client):
    response = await client.post(
        "/units/check-compatibility",
        json={"a": "km", "b": "m"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["compatible"] is True
    assert body["a_dimension"] == [0, 1, 0, 0, 0, 0, 0]
    assert body["b_dimension"] == [0, 1, 0, 0, 0, 0, 0]


@pytest.mark.asyncio
async def test_check_compatibility_kg_m(client):
    response = await client.post(
        "/units/check-compatibility",
        json={"a": "kg", "b": "m"},
    )
    assert response.status_code == 200
    assert response.json()["compatible"] is False