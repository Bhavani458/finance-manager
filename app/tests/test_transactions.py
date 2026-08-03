import io

import pytest

pytestmark = pytest.mark.asyncio


async def _account(client, headers, name="Import Acct"):
    r = await client.post(
        "/api/v1/accounts", headers=headers,
        json={"type": "checking", "name": name, "current_balance": "0"},
    )
    assert r.status_code == 201
    return r.json()


async def test_csv_import_success_and_errors(client, auth_headers):
    acct = await _account(client, auth_headers, name="Import1")
    csv_data = (
        "date,amount,merchant,category,account,notes\n"
        "2026-08-01,-30.00,Cafe,Dining,Import1,coffee\n"
        "2026-08-02,-100.00,Store,Groceries,Import1,\n"
        "notadate,-1,Bad,Groceries,Import1,\n"
        "2026-08-03,-1,Nowhere,Groceries,UnknownAcct,\n"
    )
    files = {"file": ("in.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    resp = await client.post("/api/v1/transactions/import-csv", headers=auth_headers, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert len(body["errors"]) == 2


async def test_search_and_category_filter(client, auth_headers):
    acct = await _account(client, auth_headers, name="SearchAcct")
    cats = await client.get("/api/v1/categories", headers=auth_headers)
    dining = next(c for c in cats.json() if c["name"] == "Dining")

    for i, (m, cat) in enumerate([("Pizza Palace", dining["id"]), ("Bookshop", None), ("Big Pizza", dining["id"])]):
        r = await client.post(
            "/api/v1/transactions", headers=auth_headers,
            json={
                "account_id": acct["id"],
                "date": f"2026-08-0{i+1}",
                "amount": "-10",
                "merchant_raw": m,
                "category_id": cat,
            },
        )
        assert r.status_code == 201

    r1 = await client.get(
        f"/api/v1/transactions?category_id={dining['id']}", headers=auth_headers
    )
    assert r1.status_code == 200
    assert len(r1.json()) == 2

    r2 = await client.get("/api/v1/transactions?search=pizza", headers=auth_headers)
    assert r2.status_code == 200
    assert len(r2.json()) == 2
