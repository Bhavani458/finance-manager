"""Market price valuation for stocks/ETFs.

TODO: wire up a real stock quote provider (Yahoo Finance, Alpha Vantage, NSE/BSE, etc.).
For now this is a stub: returns current_value unchanged.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute(db: AsyncSession, investment, type_obj, as_of_date: date) -> tuple[Decimal | None, Decimal]:
    logger.warning(
        "market_price valuation stub called for investment %s — returning current_value unchanged",
        investment.id,
    )
    return None, Decimal(investment.current_value or 0)
