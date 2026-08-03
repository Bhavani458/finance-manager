"""Compute and upsert a NetWorthSnapshot for every user for today."""

from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.net_worth import compute_and_snapshot


async def main() -> None:
    today = date.today()
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            await compute_and_snapshot(db, u.id, today)
        await db.commit()
        print(f"Snapshotted net worth for {len(users)} users.")


if __name__ == "__main__":
    asyncio.run(main())
