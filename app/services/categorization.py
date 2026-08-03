import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import CategorizationRule


async def apply_rules(db: AsyncSession, user_id: uuid.UUID, merchant_raw: str) -> uuid.UUID | None:
    """Case-insensitive substring match. First matching rule wins."""
    result = await db.execute(select(CategorizationRule).where(CategorizationRule.user_id == user_id))
    rules = result.scalars().all()
    m = (merchant_raw or "").lower()
    for r in rules:
        if r.match_pattern and r.match_pattern.lower() in m:
            return r.category_id
    return None
