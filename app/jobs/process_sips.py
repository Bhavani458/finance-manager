"""Process recurring SIP contributions due today."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.investment import (
    Investment,
    InvestmentTransaction,
    InvestmentTxnType,
    InvestmentType,
    ValuationMethod,
)
from app.services.market_data import amfi

_FREQ_MAP = {
    "daily": relativedelta(days=1),
    "weekly": relativedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "quarterly": relativedelta(months=3),
    "yearly": relativedelta(years=1),
    "annually": relativedelta(years=1),
}


async def main() -> None:
    today = date.today()
    async with AsyncSessionLocal() as db:
        invs = (
            await db.execute(select(Investment).where(Investment.recurring_contribution.is_not(None)))
        ).scalars().all()

        for inv in invs:
            rc = inv.recurring_contribution or {}
            next_run = rc.get("next_run_date")
            if not next_run:
                continue
            try:
                next_run_d = date.fromisoformat(next_run)
            except ValueError:
                continue
            if next_run_d > today:
                continue
            end = rc.get("end_date")
            if end:
                try:
                    if today > date.fromisoformat(end):
                        continue
                except ValueError:
                    pass

            amount = Decimal(str(rc.get("amount", 0)))
            if amount <= 0:
                continue

            type_obj = await db.get(InvestmentType, inv.investment_type_id)
            price = None
            units = None
            if type_obj and type_obj.valuation_method == ValuationMethod.NAV:
                sc = (inv.attributes or {}).get("scheme_code")
                if sc:
                    price = await amfi.get_nav(str(sc), today)
                    if price and price > 0:
                        units = (amount / price).quantize(Decimal("0.000001"))

            db.add(
                InvestmentTransaction(
                    investment_id=inv.id,
                    date=today,
                    txn_type=InvestmentTxnType.BUY,
                    units=units,
                    price_per_unit=price,
                    amount=amount,
                )
            )
            inv.invested_amount = Decimal(inv.invested_amount or 0) + amount

            freq = str(rc.get("frequency", "monthly")).lower()
            step = _FREQ_MAP.get(freq, relativedelta(months=1))
            step_up = rc.get("step_up_pct")
            new_amount = amount
            if step_up and freq == "yearly":
                new_amount = amount * (Decimal("1") + Decimal(str(step_up)) / Decimal("100"))

            rc["next_run_date"] = (next_run_d + step).isoformat()
            rc["amount"] = str(new_amount)
            inv.recurring_contribution = rc

        await db.commit()
        print("SIPs processed.")


if __name__ == "__main__":
    asyncio.run(main())
