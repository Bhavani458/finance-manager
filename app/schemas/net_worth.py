import uuid
from datetime import date as date_type
from decimal import Decimal

from app.schemas.common import ORMModel


class NetWorthOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date_type
    total_assets: Decimal
    total_liabilities: Decimal
