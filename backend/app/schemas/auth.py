"""Pydantic schemas for the auth API (Task 18)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserRegister(BaseModel):
    """Development-friendly registration — the password is never returned."""

    email: EmailStr = Field(max_length=320, description="ایمیل (نام کاربری)")
    password: str = Field(min_length=8, max_length=128, description="گذرواژه")
    full_name: str = Field(min_length=1, max_length=200, description="نام کامل")
    # NOTE: admin self-registration is intentionally rejected (see route) —
    # admins are created only via the development seed/CLI.
    role: UserRole = UserRole.doctor


class UserLogin(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public user representation — password_hash is never exposed."""

    id: int
    email: EmailStr
    phone: str | None = None
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
