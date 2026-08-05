import uuid
from datetime import date

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.services.budgets import compute_spent

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    month: date = Query(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    start = month.replace(day=1)
    end = start + relativedelta(months=1)
    spent_subq = (
        select(Transaction.category_id, func.sum(Transaction.amount).label("total"))
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.user_id == user.id,
            Transaction.amount < 0,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )
    stmt = (
        select(Budget, func.coalesce(spent_subq.c.total, 0))
        .outerjoin(spent_subq, spent_subq.c.category_id == Budget.category_id)
        .where(Budget.user_id == user.id, Budget.month == start)
    )
    rows = (await db.execute(stmt)).all()
    return [BudgetOut.model_validate({**b.__dict__, "spent": abs(Decimal(total))}) for b, total in rows]


@router.post("", response_model=BudgetOut, status_code=201)
async def create_budget(
    payload: BudgetCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    b = Budget(user_id=user.id, **payload.model_dump())
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return BudgetOut.model_validate({**b.__dict__, "spent": 0})


@router.patch("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: uuid.UUID, payload: BudgetUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    b = await db.get(Budget, budget_id)
    if b is None or b.user_id != user.id:
        raise HTTPException(status_code=404, detail="Budget not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    await db.commit()
    await db.refresh(b)
    spent = await compute_spent(db, user.id, b.category_id, b.month)
    return BudgetOut.model_validate({**b.__dict__, "spent": spent})


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    b = await db.get(Budget, budget_id)
    if b is None or b.user_id != user.id:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(b)
    await db.commit()
