from decimal import Decimal

import pytest

pytestmark = pytest.mark.asyncio


async def _get_type(client, headers, key):
    r = await client.get("/api/v1/investment-types", headers=headers)
    return next(t for t in r.json() if t["key"] == key)


async def test_allocation_total_equals_sum_of_investments(client, auth_headers):
    physical = await _get_type(client, auth_headers, "physical_asset")

    for i, cv in enumerate(["100.00", "200.50", "300.25"]):
        r = await client.post(
            "/api/v1/investments", headers=auth_headers,
            json={
                "investment_type_id": physical["id"],
                "nickname": f"asset-{i}",
                "attributes": {"asset_subtype": "collectible"},
                "invested_amount": cv,
                "current_value": cv,
            },
        )
        assert r.status_code == 201, r.text

    invs = await client.get("/api/v1/investments", headers=auth_headers)
    sum_invs = sum(Decimal(i["current_value"]) for i in invs.json())

    alloc = await client.get("/api/v1/reports/investment-allocation", headers=auth_headers)
    sum_alloc = sum(Decimal(a["total_current_value"]) for a in alloc.json())

    assert sum_invs == sum_alloc
