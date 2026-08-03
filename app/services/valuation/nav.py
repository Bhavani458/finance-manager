from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment import InvestmentTransaction, InvestmentTxnType
from app.services.market_data import amfi


async def compute(db: AsyncSession, investment, type_obj, as_of_date: date) -> tuple[Decimal | None, Decimal]:
    scheme_code = (investment.attributes or {}).get("scheme_code")
    if not scheme_code:
        return None, Decimal(investment.current_value or 0)

    nav = await amfi.get_nav(str(scheme_code), as_of_date)
    if nav is None:
        return None, Decimal(investment.current_value or 0)

    stmt = select(InvestmentTransaction).where(InvestmentTransaction.investment_id == investment.id)
    txns = (await db.execute(stmt)).scalars().all()
    units = Decimal("0")
    for t in txns:
        if t.units is None:
            continue
        if t.txn_type == InvestmentTxnType.BUY:
            units += Decimal(t.units)
        elif t.txn_type in (InvestmentTxnType.SELL, InvestmentTxnType.REDEMPTION):
            units -= Decimal(t.units)

    total = (nav * units).quantize(Decimal("0.01"))
    return nav, total
