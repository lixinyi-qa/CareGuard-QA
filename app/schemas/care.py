from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CareLinkCreate(BaseModel):
    elderly_phone: str = Field(pattern=r"^1[3-9]\d{9}$")


class CareLinkRead(BaseModel):
    id: int
    elderly_id: int
    family_id: int
    elderly_name: str
    family_name: str
    status: Literal["pending", "active", "revoked"]
    created_at: datetime
    accepted_at: datetime | None


class ContactCreate(BaseModel):
    owner_id: int | None = None
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    relationship: str = Field(min_length=1, max_length=30)
    priority: int = Field(default=1, ge=1, le=5)


class ContactRead(BaseModel):
    id: int
    owner_id: int
    name_masked: str
    phone_masked: str
    relationship: str
    priority: int
    created_at: datetime
