from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from app.models.enums import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponse"


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str
    roll_number: Optional[str] = None
    account_type: UserRole = UserRole.STUDENT

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v):
        # Only allow STUDENT role for self-registration
        # Organizer/ADMIN roles require admin approval
        if v not in [UserRole.STUDENT]:
            raise ValueError("Invalid account type. Only student registration is allowed.")
        return v

    @model_validator(mode="after")
    def validate_roll_number(self):
        # roll_number is required for STUDENT accounts
        if self.account_type == UserRole.STUDENT and not self.roll_number:
            raise ValueError("Roll number is required for student registration")
        return self


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


from app.schemas.user import UserResponse

__all__ = ['Token', 'TokenData', 'LoginRequest', 'RegisterRequest', 'VerifyEmailRequest', 'ResendVerificationRequest', 'ForgotPasswordRequest', 'ResetPasswordRequest']