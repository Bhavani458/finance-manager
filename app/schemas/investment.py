import uuid
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.investment import (
    InvestmentCategory,
    InvestmentStatus,
    InvestmentTxnType,
    ValuationMethod,
)
from app.schemas.common import ORMModel

FieldDataType = Literal["text", "number", "date", "percent", "enum"]


class FieldSchemaItem(BaseModel):
    key: str
    label: str
    data_type: FieldDataType
    required: bool = False
    options: list[str] | None = None


class InvestmentTypeCreate(BaseModel):
    key: str | None = None
    display_name: str
    category: InvestmentCategory
    valuation_method: ValuationMethod
    field_schema: list[FieldSchemaItem] = Field(default_factory=list)


class InvestmentTypePatch(BaseModel):
    display_name: str | None = None
    field_schema: list[FieldSchemaItem] | None = None


class InvestmentTypeOut(ORMModel):
    id: uuid.UUID
    key: str
    display_name: str
    category: InvestmentCategory
    valuation_method: ValuationMethod
    field_schema: list[dict[str, Any]]
    is_system: bool
    created_by_user_id: uuid.UUID | None


class InvestmentCreate(BaseModel):
    investment_type_id: uuid.UUID
    account_id: uuid.UUID | None = None
    nickname: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    invested_amount: Decimal = Decimal("0")
    current_value: Decimal = Decimal("0")
    currency: str = "INR"
    status: InvestmentStatus = InvestmentStatus.ACTIVE
    recurring_contribution: dict[str, Any] | None = None


class InvestmentPatch(BaseModel):
    nickname: str | None = None
    attributes: dict[str, Any] | None = None
    invested_amount: Decimal | None = None
    current_value: Decimal | None = None
    status: InvestmentStatus | None = None
    recurring_contribution: dict[str, Any] | None = None
    account_id: uuid.UUID | None = None


class InvestmentOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    investment_type_id: uuid.UUID
    account_id: uuid.UUID | None
    nickname: str
    attributes: dict[str, Any]
    invested_amount: Decimal
    current_value: Decimal
    currency: str
    status: InvestmentStatus
    recurring_contribution: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class InvestmentTxnCreate(BaseModel):
    date: date_type
    txn_type: InvestmentTxnType
    units: Decimal | None = None
    price_per_unit: Decimal | None = None
    amount: Decimal


class InvestmentTxnOut(ORMModel):
    id: uuid.UUID
    investment_id: uuid.UUID
    date: date_type
    txn_type: InvestmentTxnType
    units: Decimal | None
    price_per_unit: Decimal | None
    amount: Decimal
