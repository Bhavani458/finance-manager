from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession


async def compute(db: AsyncSession, investment, type_obj, as_of_date: date) -> tuple[Decimal | None, Decimal]:
    return None, Decimal(investment.current_value or 0)
