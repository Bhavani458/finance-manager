from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.models.investment import ValuationMethod
from app.services.valuation import formula_accrual, manual, nav, spot_rate

pytestmark = pytest.mark.asyncio


async def test_manual_returns_current_value_unchanged():
    inv = SimpleNamespace(current_value=Decimal("500"), attributes={}, id=None)
    typ = SimpleNamespace(valuation_method=ValuationMethod.MANUAL)
    vpu, total = await manual.compute(None, inv, typ, date.today())
    assert vpu is None
    assert total == Decimal("500")


async def test_formula_accrual_fd_1yr_10pct_quarterly():
    """100000 principal, 10% p.a. quarterly, 1 year -> ~110381 (10.381% effective)."""
    start = date(2025, 1, 1)
    end = start + timedelta(days=365)
    inv = SimpleNamespace(
        invested_amount=Decimal("100000"),
        current_value=Decimal("100000"),
        attributes={
            "interest_rate_pct": 10,
            "compounding_frequency": "quarterly",
            "start_date": start.isoformat(),
            "maturity_date": "2030-01-01",
        },
        created_at=None,
        id=None,
    )
    typ = SimpleNamespace(valuation_method=ValuationMethod.FORMULA_ACCRUAL)
    _, total = await formula_accrual.compute(None, inv, typ, end)
    assert Decimal("110000") < total < Decimal("110800")


async def test_formula_accrual_zero_elapsed_returns_principal():
    d = date(2025, 6, 1)
    inv = SimpleNamespace(
        invested_amount=Decimal("50000"),
        current_value=Decimal("50000"),
        attributes={
            "interest_rate_pct": 8,
            "compounding_frequency": "annually",
            "start_date": d.isoformat(),
        },
        created_at=None,
        id=None,
    )
    typ = SimpleNamespace(valuation_method=ValuationMethod.FORMULA_ACCRUAL)
    _, total = await formula_accrual.compute(None, inv, typ, d)
    assert total == Decimal("50000.00")


async def test_nav_with_units_and_mocked_amfi():
    from app.services.market_data import amfi as amfi_mod

    inv_id = "test-inv"
    txns = [
        SimpleNamespace(txn_type=__import__("app.models.investment", fromlist=["InvestmentTxnType"]).InvestmentTxnType.BUY,
                        units=Decimal("100"), price_per_unit=None),
    ]

    class FakeResult:
        def scalars(self):
            class S:
                def all(self_inner):
                    return txns
            return S()

    class FakeDB:
        async def execute(self, _stmt):
            return FakeResult()

    async def fake_get_nav(scheme_code, on_date=None):
        return Decimal("25")

    inv = SimpleNamespace(
        id=inv_id, current_value=Decimal("0"), attributes={"scheme_code": "12345"}
    )
    typ = SimpleNamespace(valuation_method=ValuationMethod.NAV)

    with patch.object(amfi_mod, "get_nav", side_effect=fake_get_nav):
        _, total = await nav.compute(FakeDB(), inv, typ, date.today())
    assert total == Decimal("2500.00")


async def test_nav_with_no_txns_returns_zero():
    from app.services.market_data import amfi as amfi_mod

    class FakeResult:
        def scalars(self):
            class S:
                def all(self_inner):
                    return []
            return S()

    class FakeDB:
        async def execute(self, _stmt):
            return FakeResult()

    async def fake_get_nav(*a, **k):
        return Decimal("30")

    inv = SimpleNamespace(id=None, current_value=Decimal("0"), attributes={"scheme_code": "1"})
    typ = SimpleNamespace(valuation_method=ValuationMethod.NAV)
    with patch.object(amfi_mod, "get_nav", side_effect=fake_get_nav):
        _, total = await nav.compute(FakeDB(), inv, typ, date.today())
    assert total == Decimal("0.00")


async def test_spot_rate_10g_gold():
    inv = SimpleNamespace(
        current_value=Decimal("0"),
        attributes={"metal_type": "gold", "units_grams": 10},
    )
    typ = SimpleNamespace(valuation_method=ValuationMethod.SPOT_RATE)
    _, total = await spot_rate.compute(None, inv, typ, date.today())
    assert total == Decimal("72000.00")
