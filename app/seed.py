"""Idempotent seed for system categories + 6 system InvestmentType rows."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.investment import InvestmentCategory, InvestmentType, ValuationMethod
from app.models.transaction import Category

SYSTEM_CATEGORIES = [
    "Income", "Rent", "Groceries", "Dining", "Utilities", "Transport",
    "Shopping", "Entertainment", "Healthcare", "Insurance", "Other",
]

SYSTEM_INVESTMENT_TYPES = [
    {
        "key": "fixed_deposit", "display_name": "Fixed Deposit",
        "category": InvestmentCategory.FIXED_INCOME, "valuation_method": ValuationMethod.FORMULA_ACCRUAL,
        "field_schema": [
            {"key": "bank_name", "label": "Bank Name", "data_type": "text", "required": True},
            {"key": "fd_number", "label": "FD Number", "data_type": "text", "required": True},
            {"key": "interest_rate_pct", "label": "Interest Rate %", "data_type": "percent", "required": True},
            {"key": "compounding_frequency", "label": "Compounding Frequency", "data_type": "enum",
             "required": True, "options": ["monthly", "quarterly", "annually"]},
            {"key": "maturity_date", "label": "Maturity Date", "data_type": "date", "required": True},
        ],
    },
    {
        "key": "mutual_fund", "display_name": "Mutual Fund",
        "category": InvestmentCategory.EQUITY, "valuation_method": ValuationMethod.NAV,
        "field_schema": [
            {"key": "fund_name", "label": "Fund Name", "data_type": "text", "required": True},
            {"key": "fund_house", "label": "Fund House", "data_type": "text", "required": True},
            {"key": "scheme_code", "label": "Scheme Code", "data_type": "text", "required": True},
            {"key": "folio_number", "label": "Folio Number", "data_type": "text", "required": False},
        ],
    },
    {
        "key": "bond", "display_name": "Bond",
        "category": InvestmentCategory.FIXED_INCOME, "valuation_method": ValuationMethod.FORMULA_ACCRUAL,
        "field_schema": [
            {"key": "issuer_name", "label": "Issuer Name", "data_type": "text", "required": True},
            {"key": "bond_type", "label": "Bond Type", "data_type": "enum", "required": True,
             "options": ["government", "corporate", "sovereign_gold_bond", "tax_free"]},
            {"key": "isin", "label": "ISIN", "data_type": "text", "required": False},
            {"key": "face_value", "label": "Face Value", "data_type": "number", "required": True},
            {"key": "coupon_rate_pct", "label": "Coupon Rate %", "data_type": "percent", "required": True},
            {"key": "maturity_date", "label": "Maturity Date", "data_type": "date", "required": True},
            {"key": "credit_rating", "label": "Credit Rating", "data_type": "text", "required": False},
        ],
    },
    {
        "key": "physical_asset", "display_name": "Physical Asset",
        "category": InvestmentCategory.PHYSICAL, "valuation_method": ValuationMethod.MANUAL,
        "field_schema": [
            {"key": "asset_subtype", "label": "Asset Subtype", "data_type": "enum", "required": True,
             "options": ["real_estate", "jewelry", "vehicle", "collectible"]},
            {"key": "description", "label": "Description", "data_type": "text", "required": False},
            {"key": "location", "label": "Location", "data_type": "text", "required": False},
        ],
    },
    {
        "key": "digital_metal", "display_name": "Digital Gold/Silver",
        "category": InvestmentCategory.PRECIOUS_METAL, "valuation_method": ValuationMethod.SPOT_RATE,
        "field_schema": [
            {"key": "metal_type", "label": "Metal Type", "data_type": "enum", "required": True,
             "options": ["gold", "silver"]},
            {"key": "provider", "label": "Provider", "data_type": "text", "required": True},
            {"key": "units_grams", "label": "Units (grams)", "data_type": "number", "required": True},
        ],
    },
    {
        "key": "stock", "display_name": "Stock / ETF",
        "category": InvestmentCategory.EQUITY, "valuation_method": ValuationMethod.MARKET_PRICE,
        "field_schema": [
            {"key": "ticker", "label": "Ticker", "data_type": "text", "required": True},
            {"key": "units", "label": "Units", "data_type": "number", "required": True},
        ],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing_cats = {
            c.name for c in (await db.execute(select(Category).where(Category.is_system == True))).scalars().all()  # noqa: E712
        }
        for name in SYSTEM_CATEGORIES:
            if name not in existing_cats:
                db.add(Category(name=name, is_system=True))

        existing_types = {
            t.key for t in (await db.execute(select(InvestmentType).where(InvestmentType.is_system == True))).scalars().all()  # noqa: E712
        }
        for t in SYSTEM_INVESTMENT_TYPES:
            if t["key"] not in existing_types:
                db.add(InvestmentType(**t, is_system=True))

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
