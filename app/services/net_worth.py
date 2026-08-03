import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.investment import Investment, InvestmentStatus
from app.models.net_worth import NetWorthSnapshot

ASSET_TYPES = {
    AccountType.CHECKING,
    AccountType.SAVINGS,
    AccountType.BROKERAGE,
    AccountType.RETIREMENT,
    AccountType.PROPERTY,
}
LIABILITY_TYPES = {AccountType.CREDIT, AccountType.LOAN}


async def compute_and_snapshot(db: AsyncSession, user_id: uuid.UUID, snapshot_date: date) -> NetWorthSnapshot:
    accounts = (await db.execute(select(Account).where(Account.user_id == user_id))).scalars().all()

    assets = Decimal("0")
    liabilities = Decimal("0")
    for a in accounts:
        bal = Decimal(a.current_balance or 0)
        if a.type in ASSET_TYPES and bal > 0:
            assets += bal
        elif a.type in LIABILITY_TYPES:
            liabilities += abs(bal)
        elif bal < 0:
            liabilities += abs(bal)

    inv_total = (
        await db.execute(
            select(Investment).where(
                Investment.user_id == user_id, Investment.status == InvestmentStatus.ACTIVE
            )
        )
    ).scalars().all()
    for inv in inv_total:
        assets += Decimal(inv.current_value or 0)

    existing = (
        await db.execute(
            select(NetWorthSnapshot).where(
                NetWorthSnapshot.user_id == user_id, NetWorthSnapshot.date == snapshot_date
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.total_assets = assets
        existing.total_liabilities = liabilities
        snap = existing
    else:
        snap = NetWorthSnapshot(
            user_id=user_id, date=snapshot_date, total_assets=assets, total_liabilities=liabilities
        )
        db.add(snap)
    await db.flush()
    return snap
