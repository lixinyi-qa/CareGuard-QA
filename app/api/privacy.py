from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.models import AuditLog, EmergencyContact, MoodCheckin, Reminder
from app.schemas.common import AuditRead
from app.services.audit import write_audit
from app.services.emotion import DISCLAIMER

router = APIRouter(tags=["Privacy and governance"])


@router.get("/privacy/export")
def export_my_data(db: DbSession, user: CurrentUser) -> dict:
    moods = db.scalars(select(MoodCheckin).where(MoodCheckin.user_id == user.id)).all()
    reminders = db.scalars(select(Reminder).where(Reminder.owner_id == user.id)).all()
    contacts = db.scalars(select(EmergencyContact).where(EmergencyContact.owner_id == user.id)).all()
    write_audit(db, actor_id=user.id, action="export", resource_type="privacy_data", resource_id=user.id)
    db.commit()
    return {
        "export_version": "1.0",
        "user": {"id": user.id, "name": user.name, "phone": user.phone, "role": user.role},
        "moods": [
            {"id": m.id, "text": m.text, "emotion": m.emotion, "checked_at": m.checked_at}
            for m in moods
        ],
        "reminders": [
            {"id": r.id, "title": r.title, "due_at": r.due_at, "completed": r.is_completed}
            for r in reminders
        ],
        "contacts": [
            {"id": c.id, "name": c.name, "phone": c.phone, "relationship": c.relationship}
            for c in contacts
        ],
    }


@router.get("/audit-logs/me", response_model=list[AuditRead])
def my_audit_logs(db: DbSession, user: CurrentUser, limit: int = 50) -> list[AuditLog]:
    safe_limit = min(max(limit, 1), 100)
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.actor_id == user.id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(safe_limit)
        ).all()
    )


@router.get("/ai/model-card")
def model_card() -> dict:
    return {
        "name": "CareGuard Chinese Emotion Baseline",
        "version": "1.0.0",
        "task": "three-class text emotion classification",
        "labels": ["positive", "neutral", "negative"],
        "method": "transparent lexicon and negation rules",
        "intended_use": "daily wellbeing check-in and QA demonstration",
        "out_of_scope": ["medical diagnosis", "treatment advice", "emergency dispatch"],
        "known_limitations": [
            "sarcasm and dialects may be misclassified",
            "short or ambiguous sentences default to neutral",
            "the rule set is not a clinical instrument",
        ],
        "privacy": "Raw check-in text is visible only to its owner and administrators; linked family sees labels only.",
        "disclaimer": DISCLAIMER,
    }
