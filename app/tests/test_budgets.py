from decimal import Decimal

import pytest

pytestmark = pytest.mark.asyncio


async def test_budget_spent_is_absolute_sum_of_negatives(client, auth_headers):
    cats = await client.get("/api/v1/categories", headers=auth_headers)
    groceries = next(c for c in cats.json() if c["name"] == "Groceries")

    acct = await client.post(
        "/api/v1/accounts", headers=auth_headers,
        json={"type": "checking", "name": "Main", "current_balance": "1000"},
    )
    assert acct.status_code == 201, acct.text
    acct_id = acct.json()["id"]

    bud = await client.post(
        "/api/v1/budgets", headers=auth_headers,
        json={"category_id": groceries["id"], "month": "2026-08-01", "amount": "500"},
    )
    assert bud.status_code == 201, bud.text

    for amt in ("-100", "-50", "-25"):
        r = await client.post(
            "/api/v1/transactions", headers=auth_headers,
            json={
                "account_id": acct_id,
                "date": "2026-08-15",
                "amount": amt,
                "merchant_raw": "Store",
                "category_id": groceries["id"],
            },
        )
        assert r.status_code == 201, r.text

    got = await client.get("/api/v1/budgets?month=2026-08-01", headers=auth_headers)
    assert got.status_code == 200
    row = next(b for b in got.json() if b["category_id"] == groceries["id"])
    assert Decimal(row["spent"]) == Decimal("175")
