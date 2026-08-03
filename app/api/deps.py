"""Auth + DB dependencies.

Token verification supports two modes:
- If CLERK_JWKS_URL is set, verify a Clerk RS256 JWT via JWKS (production).
- Otherwise fall back to local HS256 with JWT_SECRET (dev/tests).

The `sub` claim is treated as User.auth_provider_id.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.account import Account, AccountType
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    if settings.CLERK_JWKS_URL:
        try:
            jwks_client = jwt.PyJWKClient(settings.CLERK_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token).key
            return jwt.decode(token, signing_key, algorithms=["RS256"], options={"verify_aud": False})
        except jwt.PyJWKClientError:
            pass  # not a Clerk token — try HS256 dev fallback
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = _decode_token(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub")
    result = await db.execute(select(User).where(User.auth_provider_id == sub))
    user = result.scalar_one_or_none()
    if user is None:
        email = payload.get("email") or f"{sub}@clerk.local"
        user = User(email=email, auth_provider_id=sub)
        db.add(user)
        await db.flush()
        db.add(Account(user_id=user.id, type=AccountType.CHECKING, name="Cash", current_balance=0))
        await db.commit()
        await db.refresh(user)
    return user
