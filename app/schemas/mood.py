from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MoodCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("打卡内容不能为空")
        return value


class MoodRead(BaseModel):
    id: int
    user_id: int
    text: str | None
    emotion: Literal["positive", "neutral", "negative"]
    emotion_display: str
    confidence: int
    is_high_risk: bool
    checked_at: datetime
    disclaimer: str


class MoodStats(BaseModel):
    positive: int
    neutral: int
    negative: int
    total: int
    latest_emotion: str | None
    disclaimer: str
