import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class DevLoginIn(BaseModel):
    email: EmailStr
    auth_provider_id: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    auth_provider_id: str
    created_at: datetime
