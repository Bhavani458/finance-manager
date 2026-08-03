"""AMFI / mfapi.in client for mutual-fund NAV lookup.

Wraps https://api.mfapi.in/mf/{scheme_code}. No auth required.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def get_nav(scheme_code: str, on_date: date | None = None) -> Decimal | None:
    """Return NAV as Decimal. If on_date given, return nearest-not-after; else latest."""
    url = f"{settings.AMFI_BASE_URL.rstrip('/')}/mf/{scheme_code}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        logger.warning("AMFI fetch failed for scheme %s: %s", scheme_code, e)
        return None

    entries = payload.get("data") or []
    if not entries:
        return None

    # mfapi format: each entry {"date": "DD-MM-YYYY", "nav": "123.4567"}
    parsed = []
    for entry in entries:
        try:
            d = datetime.strptime(entry["date"], "%d-%m-%Y").date()
            nav = Decimal(str(entry["nav"]))
            parsed.append((d, nav))
        except (KeyError, ValueError):
            continue

    if not parsed:
        return None

    parsed.sort(key=lambda x: x[0], reverse=True)

    if on_date is None:
        return parsed[0][1]

    for d, nav in parsed:
        if d <= on_date:
            return nav
    return None
