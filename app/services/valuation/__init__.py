"""Valuation dispatch registry.

Each strategy: async (db, investment, type_obj, as_of_date) -> (value_per_unit, total_value)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment import Investment, InvestmentType, ValuationMethod

from . import formula_accrual, manual, market_price, nav, spot_rate

_REGISTRY = {
    ValuationMethod.MANUAL: manual.compute,
    ValuationMethod.NAV: nav.compute,
    ValuationMethod.SPOT_RATE: spot_rate.compute,
    ValuationMethod.FORMULA_ACCRUAL: formula_accrual.compute,
    ValuationMethod.MARKET_PRICE: market_price.compute,
}


async def compute_valuation(
    db: AsyncSession,
    investment: Investment,
    type_obj: InvestmentType,
    as_of_date: date,
) -> tuple[Decimal | None, Decimal]:
    fn = _REGISTRY[type_obj.valuation_method]
    return await fn(db, investment, type_obj, as_of_date)
