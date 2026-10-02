from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import UserRole


class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole = UserRole.STUDENT


class UserCreate(UserBase):
    password_hash: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
