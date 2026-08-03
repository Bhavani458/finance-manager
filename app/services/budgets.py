import uuid
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction


async def compute_spent(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID, month: date
) -> Decimal:
    """Sum absolute value of Transaction.amount where amount<0 within the month."""
    start = month.replace(day=1)
    end = start + relativedelta(months=1)
    stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.amount < 0,
            Transaction.date >= start,
            Transaction.date < end,
        )
    )
    total = (await db.execute(stmt)).scalar_one()
    return abs(Decimal(total))
