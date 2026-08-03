import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.transaction import CategorizationRule, Category
from app.models.user import User
from app.schemas.transaction import CategoryCreate, CategoryOut, RuleCreate, RuleOut, RuleUpdate

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = list((await db.execute(select(Category))).scalars().all())
    by_id = {c.id: {"id": c.id, "name": c.name, "parent_id": c.parent_id, "icon": c.icon,
                    "is_system": c.is_system, "children": []} for c in rows}
    roots = []
    for c in rows:
        d = by_id[c.id]
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id]["children"].append(d)
        else:
            roots.append(d)
    return roots


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    payload: CategoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    c = Category(**payload.model_dump(), is_system=False)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name, "parent_id": c.parent_id, "icon": c.icon,
            "is_system": c.is_system, "children": []}


# CategorizationRules
@router.get("/categorization-rules", response_model=list[RuleOut])
async def list_rules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(CategorizationRule).where(CategorizationRule.user_id == user.id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/categorization-rules", response_model=RuleOut, status_code=201)
async def create_rule(
    payload: RuleCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    r = CategorizationRule(user_id=user.id, **payload.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.patch("/categorization-rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: uuid.UUID, payload: RuleUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    r = await db.get(CategorizationRule, rule_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/categorization-rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    r = await db.get(CategorizationRule, rule_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(r)
    await db.commit()
