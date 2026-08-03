"""Auth routes.

/auth/dev-login is DEV-ONLY (guarded by settings.ENV == "dev"). It upserts a User
row and returns a signed HS256 JWT so tests + local dev can hit protected routes
without running a real Clerk instance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.account import Account, AccountType
from app.models.user import User
from app.schemas.user import DevLoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=TokenOut)
async def dev_login(payload: DevLoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    if settings.ENV not in ("dev", "test"):
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(select(User).where(User.auth_provider_id == payload.auth_provider_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=payload.email, auth_provider_id=payload.auth_provider_id)
        db.add(user)
        await db.flush()
        db.add(Account(user_id=user.id, type=AccountType.CHECKING, name="Cash", current_balance=0))
        await db.commit()
        await db.refresh(user)

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user.auth_provider_id, "iat": int(now.timestamp()), "exp": int((now + timedelta(days=30)).timestamp())},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return TokenOut(access_token=token)
