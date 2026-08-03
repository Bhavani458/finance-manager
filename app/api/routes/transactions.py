import csv
import io
import uuid
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.transaction import Category, Transaction, TransactionSource
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from app.services.categorization import apply_rules

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _user_account_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    r = await db.execute(select(Account.id).where(Account.user_id == user_id))
    return [row[0] for row in r.all()]


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    category_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    search: str | None = None,
    from_: date_type | None = Query(default=None, alias="from"),
    to: date_type | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_ids = await _user_account_ids(db, user.id)
    if not account_ids:
        return []
    stmt = select(Transaction).where(Transaction.account_id.in_(account_ids))
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    if search:
        pat = f"%{search}%"
        stmt = stmt.where(
            or_(
                Transaction.merchant_raw.ilike(pat),
                Transaction.merchant_clean.ilike(pat),
                Transaction.notes.ilike(pat),
            )
        )
    if from_:
        stmt = stmt.where(Transaction.date >= from_)
    if to:
        stmt = stmt.where(Transaction.date <= to)
    stmt = stmt.order_by(Transaction.date.desc()).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(Account, payload.account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")

    data = payload.model_dump()
    if data.get("category_id") is None:
        data["category_id"] = await apply_rules(db, user.id, data["merchant_raw"])

    t = Transaction(**data)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@router.patch("/{txn_id}", response_model=TransactionOut)
async def update_transaction(
    txn_id: uuid.UUID, payload: TransactionUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    t = await db.get(Transaction, txn_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account = await db.get(Account, t.account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return t


@router.delete("/{txn_id}", status_code=204)
async def delete_transaction(
    txn_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    t = await db.get(Transaction, txn_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Not found")
    account = await db.get(Account, t.account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(t)
    await db.commit()


@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV header: date,amount,merchant,category,account,notes"""
    contents = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(contents))

    # Preload user's accounts + categories for name lookup
    accts = {a.name: a for a in (await db.execute(select(Account).where(Account.user_id == user.id))).scalars().all()}
    cats = {c.name.lower(): c for c in (await db.execute(select(Category))).scalars().all()}

    imported = 0
    errors: list[dict] = []
    for i, row in enumerate(reader, start=2):
        try:
            acct_name = (row.get("account") or "").strip()
            acct = accts.get(acct_name)
            if acct is None:
                raise ValueError(f"Unknown account '{acct_name}'")
            try:
                amount = Decimal(str(row.get("amount", "")).strip())
            except InvalidOperation as e:
                raise ValueError(f"Bad amount: {row.get('amount')}") from e
            d = date_type.fromisoformat(str(row.get("date", "")).strip())
            merchant = (row.get("merchant") or "").strip()
            notes = row.get("notes") or None

            cat_id = None
            cat_name = (row.get("category") or "").strip().lower()
            if cat_name and cat_name in cats:
                cat_id = cats[cat_name].id
            elif not cat_id:
                cat_id = await apply_rules(db, user.id, merchant)

            t = Transaction(
                account_id=acct.id,
                date=d,
                amount=amount,
                merchant_raw=merchant,
                category_id=cat_id,
                notes=notes,
                source=TransactionSource.CSV,
            )
            db.add(t)
            imported += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    await db.commit()
    return {"imported": imported, "errors": errors}
