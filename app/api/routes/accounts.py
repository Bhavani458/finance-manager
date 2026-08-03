import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    limit: int = Query(50, le=200), offset: int = 0,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    stmt = select(Account).where(Account.user_id == user.id).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=AccountOut, status_code=201)
async def create_account(
    payload: AccountCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    a = Account(user_id=user.id, **payload.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: uuid.UUID, payload: AccountUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    a = await db.get(Account, account_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return a


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    a = await db.get(Account, account_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(a)
    await db.commit()
