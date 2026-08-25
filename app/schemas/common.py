from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MessageResponse(BaseModel):
    code: str
    message: str


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str | None = None


class AuditRead(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: int | None
    outcome: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
