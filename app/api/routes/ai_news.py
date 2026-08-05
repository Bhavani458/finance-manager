from datetime import datetime, timedelta, timezone

import litellm
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.ai_news import AiNewsCache
from app.models.investment import Investment, InvestmentType
from app.models.user import User

router = APIRouter(prefix="/ai-news", tags=["ai-news"])


def _serialize(cache: AiNewsCache, is_cached: bool) -> dict:
    return {
        "content": cache.content,
        "generated_at": cache.generated_at.isoformat(),
        "is_cached": is_cached,
    }


async def _generate(user: User, db: AsyncSession) -> AiNewsCache:
    stmt = (
        select(InvestmentType.display_name, InvestmentType.category)
        .join(Investment, Investment.investment_type_id == InvestmentType.id)
        .where(Investment.user_id == user.id)
        .distinct()
    )
    held = list((await db.execute(stmt)).all())

    if held:
        portfolio_desc = ", ".join(f"{name} ({category.value})" for name, category in held)
    else:
        portfolio_desc = "no investments yet"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial content assistant producing general educational market "
                "commentary for an Indian retail investor. You are not giving personalized "
                "financial advice, and you have no access to live news — write general, "
                "well-informed commentary rather than claiming anything is breaking or "
                "happening 'today'. Always respond in well-structured markdown with headings, "
                "bold key terms, and bullet lists. Never respond as plain unformatted prose."
            ),
        },
        {
            "role": "user",
            "content": (
                f"The user currently holds these investment types: {portfolio_desc}.\n\n"
                "Write two markdown sections:\n\n"
                "## Portfolio Commentary\n"
                "2-4 bullet points of commentary specifically relevant to the investment types "
                "listed above (e.g. how that asset class tends to behave, current rate/market "
                "themes worth knowing, things to watch).\n\n"
                "## New Opportunities to Explore\n"
                "4-6 bullet points, each naming a *specific* investment idea the user does not "
                "already hold (name concrete instruments/categories such as specific mutual fund "
                "categories, bond types, gold instruments like SGBs, index funds, REITs, etc. — "
                "not generic advice like 'diversify your portfolio'). Bold the name of each idea "
                "and follow with a one-sentence rationale.\n\n"
                "Be specific and concrete, not generic filler."
            ),
        },
    ]
    response = await litellm.acompletion(
        model=settings.AI_MODEL, messages=messages, temperature=0.7, max_tokens=900
    )
    content = response.choices[0].message.content

    cache = await db.scalar(select(AiNewsCache).where(AiNewsCache.user_id == user.id))
    now = datetime.now(timezone.utc)
    if cache is None:
        cache = AiNewsCache(user_id=user.id, content=content, generated_at=now)
        db.add(cache)
    else:
        cache.content = content
        cache.generated_at = now

    await db.commit()
    await db.refresh(cache)
    return cache


@router.get("")
async def get_ai_news(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache = await db.scalar(select(AiNewsCache).where(AiNewsCache.user_id == user.id))
    if cache is not None:
        age = datetime.now(timezone.utc) - cache.generated_at
        if age < timedelta(hours=settings.AI_NEWS_CACHE_TTL_HOURS):
            return _serialize(cache, is_cached=True)

    cache = await _generate(user, db)
    return _serialize(cache, is_cached=False)


@router.post("/refresh")
async def refresh_ai_news(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache = await _generate(user, db)
    return _serialize(cache, is_cached=False)
