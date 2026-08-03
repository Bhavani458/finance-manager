import pytest

pytestmark = pytest.mark.asyncio


async def test_create_custom_type_and_additive_patch(client, auth_headers):
    resp = await client.post(
        "/api/v1/investment-types",
        headers=auth_headers,
        json={
            "display_name": "Crypto Coin",
            "category": "other",
            "valuation_method": "manual",
            "field_schema": [
                {"key": "symbol", "label": "Symbol", "data_type": "text", "required": True},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    t = resp.json()
    tid = t["id"]

    # additive patch OK
    add_resp = await client.patch(
        f"/api/v1/investment-types/{tid}",
        headers=auth_headers,
        json={
            "field_schema": [
                {"key": "symbol", "label": "Symbol", "data_type": "text", "required": True},
                {"key": "exchange", "label": "Exchange", "data_type": "text", "required": False},
            ]
        },
    )
    assert add_resp.status_code == 200, add_resp.text
    assert len(add_resp.json()["field_schema"]) == 2

    # remove field -> 409
    remove_resp = await client.patch(
        f"/api/v1/investment-types/{tid}",
        headers=auth_headers,
        json={"field_schema": [{"key": "symbol", "label": "Symbol", "data_type": "text", "required": True}]},
    )
    assert remove_resp.status_code == 409

    # rename field -> 409 (rename = remove old key)
    rename_resp = await client.patch(
        f"/api/v1/investment-types/{tid}",
        headers=auth_headers,
        json={
            "field_schema": [
                {"key": "ticker", "label": "Ticker", "data_type": "text", "required": True},
                {"key": "exchange", "label": "Exchange", "data_type": "text", "required": False},
            ]
        },
    )
    assert rename_resp.status_code == 409
