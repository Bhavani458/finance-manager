import pytest

pytestmark = pytest.mark.asyncio


async def _get_type(client, headers, key):
    r = await client.get("/api/v1/investment-types", headers=headers)
    for t in r.json():
        if t["key"] == key:
            return t
    return None


async def test_create_valid_investment_and_patch_merge(client, auth_headers):
    fd = await _get_type(client, auth_headers, "fixed_deposit")
    assert fd

    resp = await client.post(
        "/api/v1/investments",
        headers=auth_headers,
        json={
            "investment_type_id": fd["id"],
            "nickname": "SBI FD",
            "attributes": {
                "bank_name": "SBI",
                "fd_number": "123",
                "interest_rate_pct": 7.5,
                "compounding_frequency": "quarterly",
                "maturity_date": "2028-01-01",
            },
            "invested_amount": "100000",
            "current_value": "100000",
        },
    )
    assert resp.status_code == 201, resp.text
    inv_id = resp.json()["id"]

    # missing required -> 422
    bad = await client.post(
        "/api/v1/investments",
        headers=auth_headers,
        json={
            "investment_type_id": fd["id"],
            "nickname": "Bad",
            "attributes": {"bank_name": "SBI"},
        },
    )
    assert bad.status_code == 422

    # PATCH merges attributes (only override interest rate; other fields preserved)
    patch = await client.patch(
        f"/api/v1/investments/{inv_id}",
        headers=auth_headers,
        json={"attributes": {"interest_rate_pct": 8.0}},
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["attributes"]["bank_name"] == "SBI"
    assert float(body["attributes"]["interest_rate_pct"]) == 8.0


async def test_additive_schema_change_keeps_old_investments_working(client, auth_headers):
    # Create custom type
    tr = await client.post(
        "/api/v1/investment-types",
        headers=auth_headers,
        json={
            "display_name": "Widget Fund",
            "category": "other",
            "valuation_method": "manual",
            "field_schema": [
                {"key": "code", "label": "Code", "data_type": "text", "required": True},
            ],
        },
    )
    assert tr.status_code == 201, tr.text
    tid = tr.json()["id"]

    inv = await client.post(
        "/api/v1/investments",
        headers=auth_headers,
        json={
            "investment_type_id": tid,
            "nickname": "old-row",
            "attributes": {"code": "ABC"},
        },
    )
    assert inv.status_code == 201, inv.text
    inv_id = inv.json()["id"]

    # additive change adds a new optional field
    add = await client.patch(
        f"/api/v1/investment-types/{tid}",
        headers=auth_headers,
        json={
            "field_schema": [
                {"key": "code", "label": "Code", "data_type": "text", "required": True},
                {"key": "note", "label": "Note", "data_type": "text", "required": False},
            ]
        },
    )
    assert add.status_code == 200

    # old row still works — GET succeeds
    got = await client.get(f"/api/v1/investments/{inv_id}", headers=auth_headers)
    assert got.status_code == 200
