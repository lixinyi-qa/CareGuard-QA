from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ReminderCreate(BaseModel):
    owner_id: int | None = None
    title: str = Field(min_length=1, max_length=100)
    reminder_type: Literal["medication", "schedule"]
    due_at: datetime
    recurrence: Literal["once", "daily", "weekly"] = "once"
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("提醒标题不能为空")
        return value


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    due_at: datetime | None = None
    recurrence: Literal["once", "daily", "weekly"] | None = None
    notes: str | None = Field(default=None, max_length=500)
    is_completed: bool | None = None


class ReminderRead(BaseModel):
    id: int
    owner_id: int
    created_by: int
    title: str
    reminder_type: str
    due_at: datetime
    recurrence: str
    notes: str | None
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRead(BaseModel):
    id: int
    owner_id: int
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None

    model_config = {"from_attributes": True}
