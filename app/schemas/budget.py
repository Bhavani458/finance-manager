import uuid
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import ORMModel


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    month: date_type
    amount: Decimal
    rollover_enabled: bool = False


class BudgetUpdate(BaseModel):
    amount: Decimal | None = None
    rollover_enabled: bool | None = None


class BudgetOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    month: date_type
    amount: Decimal
    rollover_enabled: bool
    spent: Decimal = Decimal("0")
