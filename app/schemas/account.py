import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.account import AccountType
from app.schemas.common import ORMModel


class AccountCreate(BaseModel):
    institution_id: uuid.UUID | None = None
    type: AccountType
    name: str
    current_balance: Decimal = Decimal("0")
    currency: str = "INR"


class AccountUpdate(BaseModel):
    institution_id: uuid.UUID | None = None
    type: AccountType | None = None
    name: str | None = None
    current_balance: Decimal | None = None
    currency: str | None = None


class AccountOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    institution_id: uuid.UUID | None
    type: AccountType
    name: str
    current_balance: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
