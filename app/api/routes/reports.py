from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.investment import Investment, InvestmentType
from app.models.net_worth import NetWorthSnapshot
from app.models.transaction import Category, Transaction
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/net-worth")
async def net_worth(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NetWorthSnapshot).where(NetWorthSnapshot.user_id == user.id)
    if from_:
        stmt = stmt.where(NetWorthSnapshot.date >= from_)
    if to:
        stmt = stmt.where(NetWorthSnapshot.date <= to)
    stmt = stmt.order_by(NetWorthSnapshot.date.asc())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "date": r.date.isoformat(),
            "total_assets": str(r.total_assets),
            "total_liabilities": str(r.total_liabilities),
            "net_worth": str(Decimal(r.total_assets) - Decimal(r.total_liabilities)),
        }
        for r in rows
    ]


@router.get("/spending-by-category")
async def spending_by_category(
    month: date = Query(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    start = month.replace(day=1)
    end = start + relativedelta(months=1)
    stmt = (
        select(Category.id, Category.name, func.coalesce(func.sum(Transaction.amount), 0))
        .join(Transaction, Transaction.category_id == Category.id)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.user_id == user.id,
            Transaction.amount < 0,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Category.id, Category.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"category_id": str(cid), "category_name": name, "total_spent": str(abs(Decimal(total)))}
        for cid, name, total in rows
    ]


@router.get("/investment-allocation")
async def investment_allocation(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(
            InvestmentType.id,
            InvestmentType.key,
            InvestmentType.display_name,
            InvestmentType.category,
            func.coalesce(func.sum(Investment.invested_amount), 0),
            func.coalesce(func.sum(Investment.current_value), 0),
            func.count(Investment.id),
        )
        .join(Investment, Investment.investment_type_id == InvestmentType.id)
        .where(Investment.user_id == user.id)
        .group_by(InvestmentType.id, InvestmentType.key, InvestmentType.display_name, InvestmentType.category)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "investment_type_id": str(tid),
            "key": key,
            "display_name": name,
            "category": cat.value if hasattr(cat, "value") else cat,
            "total_invested": str(Decimal(inv)),
            "total_current_value": str(Decimal(cur)),
            "count": count,
        }
        for tid, key, name, cat, inv, cur, count in rows
    ]
