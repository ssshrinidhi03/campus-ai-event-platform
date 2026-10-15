from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import UserRole


class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole = UserRole.STUDENT
    roll_number: Optional[str] = None
    is_verified: bool = False
    is_identity_verified: bool = False


class UserCreate(UserBase):
    password_hash: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
