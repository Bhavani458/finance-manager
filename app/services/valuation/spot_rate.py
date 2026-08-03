from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data import metals


async def compute(db: AsyncSession, investment, type_obj, as_of_date: date) -> tuple[Decimal | None, Decimal]:
    attrs = investment.attributes or {}
    metal = attrs.get("metal_type")
    grams = attrs.get("units_grams") or 0
    if not metal:
        return None, Decimal(investment.current_value or 0)
    rate = await metals.get_spot_rate(str(metal), as_of_date)
    total = (Decimal(str(grams)) * rate).quantize(Decimal("0.01"))
    return rate, total
