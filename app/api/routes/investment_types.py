import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investment import InvestmentType
from app.models.user import User
from app.schemas.investment import InvestmentTypeCreate, InvestmentTypeOut, InvestmentTypePatch
from app.services.schema_validation import validate_additive_schema_change

router = APIRouter(prefix="/investment-types", tags=["investment-types"])


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


@router.get("", response_model=list[InvestmentTypeOut])
async def list_types(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(InvestmentType).where(
        or_(InvestmentType.is_system == True, InvestmentType.created_by_user_id == user.id)  # noqa: E712
    )
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=InvestmentTypeOut, status_code=201)
async def create_type(
    payload: InvestmentTypeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = payload.key or _slugify(payload.display_name)
    existing = (await db.execute(select(InvestmentType).where(InvestmentType.key == key))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Key '{key}' already exists")

    t = InvestmentType(
        key=key,
        display_name=payload.display_name,
        category=payload.category,
        valuation_method=payload.valuation_method,
        field_schema=[f.model_dump() for f in payload.field_schema],
        is_system=False,
        created_by_user_id=user.id,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@router.patch("/{type_id}", response_model=InvestmentTypeOut)
async def patch_type(
    type_id: uuid.UUID,
    payload: InvestmentTypePatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(InvestmentType, type_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Type not found")
    if t.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system type")
    if t.created_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not owner")

    if payload.display_name is not None:
        t.display_name = payload.display_name

    if payload.field_schema is not None:
        new_schema = [f.model_dump() for f in payload.field_schema]
        try:
            validate_additive_schema_change(t.field_schema or [], new_schema)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        t.field_schema = new_schema

    await db.commit()
    await db.refresh(t)
    return t
