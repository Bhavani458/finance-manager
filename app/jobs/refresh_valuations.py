"""Refresh valuations for every active investment, upserting today's snapshot."""

from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.investment import Investment, InvestmentStatus, InvestmentType, InvestmentValuation
from app.services.valuation import compute_valuation


async def main() -> None:
    today = date.today()
    async with AsyncSessionLocal() as db:
        invs = (await db.execute(select(Investment).where(Investment.status == InvestmentStatus.ACTIVE))).scalars().all()
        for inv in invs:
            type_obj = await db.get(InvestmentType, inv.investment_type_id)
            if type_obj is None:
                continue
            vpu, total = await compute_valuation(db, inv, type_obj, today)

            existing = (
                await db.execute(
                    select(InvestmentValuation).where(
                        InvestmentValuation.investment_id == inv.id,
                        InvestmentValuation.date == today,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.value_per_unit = vpu
                existing.total_value = total
            else:
                db.add(
                    InvestmentValuation(
                        investment_id=inv.id, date=today, value_per_unit=vpu, total_value=total
                    )
                )
            inv.current_value = total
        await db.commit()
        print(f"Valued {len(invs)} investments.")


if __name__ == "__main__":
    asyncio.run(main())
