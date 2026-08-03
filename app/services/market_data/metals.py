"""Precious metals spot rate lookup.

TODO: swap this stub for a real provider (e.g. metals-api.com, GoldAPI).
For now, return fixture values so the valuation engine works end-to-end.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)

# INR per gram — placeholder fixture data
_SPOT_FIXTURES: dict[str, Decimal] = {
    "gold": Decimal("7200"),
    "silver": Decimal("95"),
}


async def get_spot_rate(metal: str, on_date: date | None = None) -> Decimal:
    key = (metal or "").lower()
    if key not in _SPOT_FIXTURES:
        logger.warning("Unknown metal %r, defaulting to 0", metal)
        return Decimal("0")
    return _SPOT_FIXTURES[key]
