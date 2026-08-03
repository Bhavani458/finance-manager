"""Formula-based accrual for FDs and bonds — compound interest."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

_COMPOUNDS_PER_YEAR = {
    "monthly": Decimal("12"),
    "quarterly": Decimal("4"),
    "annually": Decimal("1"),
    "annual": Decimal("1"),
    "yearly": Decimal("1"),
}


def _parse_date(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


async def compute(db: AsyncSession, investment, type_obj, as_of_date: date) -> tuple[Decimal | None, Decimal]:
    attrs = investment.attributes or {}
    principal = Decimal(investment.invested_amount or 0)

    rate_pct = attrs.get("interest_rate_pct") or attrs.get("coupon_rate_pct") or 0
    rate = Decimal(str(rate_pct)) / Decimal("100")

    freq_key = str(attrs.get("compounding_frequency", "annually")).lower()
    n = _COMPOUNDS_PER_YEAR.get(freq_key, Decimal("1"))

    start = _parse_date(attrs.get("start_date"))
    if start is None and investment.created_at is not None:
        start = investment.created_at.date() if hasattr(investment.created_at, "date") else investment.created_at
    if start is None:
        start = as_of_date

    maturity = _parse_date(attrs.get("maturity_date"))
    effective_end = as_of_date
    if maturity is not None and as_of_date > maturity:
        effective_end = maturity

    days = max((effective_end - start).days, 0)
    if days == 0 or rate == 0:
        return None, principal.quantize(Decimal("0.01"))

    years = Decimal(days) / Decimal("365")
    # A = P * (1 + r/n)^(n*t)
    base = Decimal("1") + (rate / n)
    exponent = n * years
    # Compute base ** exponent via ln/exp with Decimal precision (approximate is fine at 2dp)
    total = principal * (base ** exponent) if exponent == exponent.to_integral_value() else principal * Decimal(
        float(base) ** float(exponent)
    )
    return None, Decimal(total).quantize(Decimal("0.01"))
