from datetime import datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.models import Alert, Reminder, User
from app.schemas.reminder import AlertRead, ReminderCreate, ReminderRead, ReminderUpdate
from app.services.access import has_active_care_link
from app.services.audit import write_audit

router = APIRouter(tags=["Reminders and alerts"])


def _owner_or_403(db: DbSession, user: User, owner_id: int) -> None:
    owner = db.get(User, owner_id)
    if owner is None or owner.role != "elderly":
        raise HTTPException(status_code=404, detail={"code": "OWNER_NOT_FOUND", "message": "老人账号不存在"})
    if not has_active_care_link(db, user, owner_id):
        raise HTTPException(status_code=403, detail={"code": "REMINDER_FORBIDDEN", "message": "无权操作该用户的提醒"})


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderCreate, db: DbSession, user: CurrentUser) -> Reminder:
    owner_id = payload.owner_id or user.id
    _owner_or_403(db, user, owner_id)
    reminder = Reminder(
        owner_id=owner_id,
        created_by=user.id,
        title=payload.title,
        reminder_type=payload.reminder_type,
        due_at=payload.due_at,
        recurrence=payload.recurrence,
        notes=payload.notes,
    )
    db.add(reminder)
    db.flush()
    write_audit(db, actor_id=user.id, action="create", resource_type="reminder", resource_id=reminder.id)
    db.commit()
    return reminder


@router.get("/reminders", response_model=list[ReminderRead])
def list_reminders(db: DbSession, user: CurrentUser, owner_id: int | None = None) -> list[Reminder]:
    target_id = owner_id or user.id
    _owner_or_403(db, user, target_id)
    return list(
        db.scalars(
            select(Reminder)
            .where(Reminder.owner_id == target_id)
            .order_by(Reminder.is_completed, Reminder.due_at, Reminder.id)
        ).all()
    )


@router.patch("/reminders/{reminder_id}", response_model=ReminderRead)
def update_reminder(
    reminder_id: int, payload: ReminderUpdate, db: DbSession, user: CurrentUser
) -> Reminder:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail={"code": "REMINDER_NOT_FOUND", "message": "提醒不存在"})
    _owner_or_403(db, user, reminder.owner_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    write_audit(db, actor_id=user.id, action="update", resource_type="reminder", resource_id=reminder.id)
    db.commit()
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: int, db: DbSession, user: CurrentUser) -> Response:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail={"code": "REMINDER_NOT_FOUND", "message": "提醒不存在"})
    _owner_or_403(db, user, reminder.owner_id)
    write_audit(db, actor_id=user.id, action="delete", resource_type="reminder", resource_id=reminder.id)
    db.delete(reminder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(db: DbSession, user: CurrentUser, owner_id: int | None = None) -> list[Alert]:
    target_id = owner_id or user.id
    if not has_active_care_link(db, user, target_id):
        raise HTTPException(status_code=403, detail={"code": "ALERT_FORBIDDEN", "message": "无权查看该用户的关怀提醒"})
    return list(
        db.scalars(
            select(Alert)
            .where(Alert.owner_id == target_id)
            .order_by(Alert.status, Alert.created_at.desc(), Alert.id.desc())
        ).all()
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(alert_id: int, db: DbSession, user: CurrentUser) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "关怀提醒不存在"})
    if not has_active_care_link(db, user, alert.owner_id):
        raise HTTPException(status_code=403, detail={"code": "ALERT_FORBIDDEN", "message": "无权处理该关怀提醒"})
    if alert.status == "acknowledged":
        raise HTTPException(status_code=409, detail={"code": "ALREADY_ACKNOWLEDGED", "message": "该提醒已经处理"})
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now()
    alert.acknowledged_by = user.id
    write_audit(db, actor_id=user.id, action="acknowledge", resource_type="alert", resource_id=alert.id)
    db.commit()
    return alert
