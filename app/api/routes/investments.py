import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investment import (
    Investment,
    InvestmentStatus,
    InvestmentTransaction,
    InvestmentType,
)
from app.models.user import User
from app.schemas.investment import (
    InvestmentCreate,
    InvestmentOut,
    InvestmentPatch,
    InvestmentTxnCreate,
    InvestmentTxnOut,
)
from app.services.schema_validation import validate_attributes

router = APIRouter(prefix="/investments", tags=["investments"])


async def _load_type_or_404(db: AsyncSession, type_id: uuid.UUID) -> InvestmentType:
    t = await db.get(InvestmentType, type_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Investment type not found")
    return t


@router.get("", response_model=list[InvestmentOut])
async def list_investments(
    investment_type_id: uuid.UUID | None = None,
    status: InvestmentStatus | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Investment).where(Investment.user_id == user.id)
    if investment_type_id:
        stmt = stmt.where(Investment.investment_type_id == investment_type_id)
    if status:
        stmt = stmt.where(Investment.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=InvestmentOut, status_code=201)
async def create_investment(
    payload: InvestmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    type_obj = await _load_type_or_404(db, payload.investment_type_id)
    try:
        validate_attributes(type_obj.field_schema or [], payload.attributes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    inv = Investment(user_id=user.id, **payload.model_dump())
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.get("/{inv_id}", response_model=InvestmentOut)
async def get_investment(
    inv_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investment, inv_id)
    if inv is None or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    return inv


@router.patch("/{inv_id}", response_model=InvestmentOut)
async def patch_investment(
    inv_id: uuid.UUID,
    payload: InvestmentPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await db.get(Investment, inv_id)
    if inv is None or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investment not found")

    data = payload.model_dump(exclude_unset=True)

    if "attributes" in data and data["attributes"] is not None:
        merged = {**(inv.attributes or {}), **data["attributes"]}
        type_obj = await _load_type_or_404(db, inv.investment_type_id)
        try:
            validate_attributes(type_obj.field_schema or [], merged)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        inv.attributes = merged
        data.pop("attributes")

    for k, v in data.items():
        setattr(inv, k, v)

    await db.commit()
    await db.refresh(inv)
    return inv


@router.delete("/{inv_id}", status_code=204)
async def delete_investment(
    inv_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investment, inv_id)
    if inv is None or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    await db.delete(inv)
    await db.commit()


@router.get("/{inv_id}/transactions", response_model=list[InvestmentTxnOut])
async def list_inv_txns(
    inv_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investment, inv_id)
    if inv is None or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    stmt = select(InvestmentTransaction).where(InvestmentTransaction.investment_id == inv_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/{inv_id}/transactions", response_model=InvestmentTxnOut, status_code=201)
async def create_inv_txn(
    inv_id: uuid.UUID, payload: InvestmentTxnCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    inv = await db.get(Investment, inv_id)
    if inv is None or inv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    t = InvestmentTransaction(investment_id=inv_id, **payload.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t
