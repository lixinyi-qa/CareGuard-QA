import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str = Field(min_length=8, max_length=72)
    role: Literal["elderly", "family"]
    consent: bool

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("密码必须同时包含字母和数字")
        return value

    @field_validator("consent")
    @classmethod
    def require_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("必须同意隐私说明后才能注册")
        return value


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str = Field(min_length=1, max_length=72)


class UserRead(BaseModel):
    id: int
    name: str
    phone_masked: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
