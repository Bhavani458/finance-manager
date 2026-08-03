import uuid
from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.transaction import TransactionSource
from app.schemas.common import ORMModel


class TransactionCreate(BaseModel):
    account_id: uuid.UUID
    date: date_type
    amount: Decimal
    merchant_raw: str
    merchant_clean: str | None = None
    category_id: uuid.UUID | None = None
    is_recurring: bool = False
    notes: str | None = None
    source: TransactionSource = TransactionSource.MANUAL


class TransactionUpdate(BaseModel):
    date: date_type | None = None
    amount: Decimal | None = None
    merchant_raw: str | None = None
    merchant_clean: str | None = None
    category_id: uuid.UUID | None = None
    is_recurring: bool | None = None
    notes: str | None = None


class TransactionOut(ORMModel):
    id: uuid.UUID
    account_id: uuid.UUID
    date: date_type
    amount: Decimal
    merchant_raw: str
    merchant_clean: str | None
    category_id: uuid.UUID | None
    is_recurring: bool
    notes: str | None
    source: TransactionSource
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None
    icon: str | None = None


class CategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    icon: str | None
    is_system: bool
    children: list["CategoryOut"] = []


class RuleCreate(BaseModel):
    match_pattern: str
    category_id: uuid.UUID


class RuleUpdate(BaseModel):
    match_pattern: str | None = None
    category_id: uuid.UUID | None = None


class RuleOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    match_pattern: str
    category_id: uuid.UUID
