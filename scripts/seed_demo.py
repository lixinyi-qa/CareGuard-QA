"""Idempotently seed a complete elderly/family demonstration relationship."""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import CareLink, EmergencyContact, MoodCheckin, Reminder, User
from app.services.emotion import classify_emotion


def get_or_create_user(db, *, name: str, phone: str, role: str) -> User:
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(name=name, phone=phone, role=role, password_hash=hash_password("Care1234"))
        db.add(user)
        db.flush()
    return user


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        elderly = get_or_create_user(db, name="王安心", phone="13800000001", role="elderly")
        family = get_or_create_user(db, name="王小爱", phone="13800000002", role="family")

        link = db.scalar(
            select(CareLink).where(
                CareLink.elderly_id == elderly.id, CareLink.family_id == family.id
            )
        )
        if link is None:
            db.add(
                CareLink(
                    elderly_id=elderly.id,
                    family_id=family.id,
                    status="active",
                    accepted_at=datetime.now(),
                )
            )

        if not db.scalar(select(MoodCheckin).where(MoodCheckin.user_id == elderly.id)):
            for index, text in enumerate(
                ["今天和老朋友散步，我很开心", "今天在家看了电视", "昨晚有点失眠和担心"]
            ):
                result = classify_emotion(text)
                db.add(
                    MoodCheckin(
                        user_id=elderly.id,
                        text=text,
                        emotion=result.label,
                        confidence=result.confidence,
                        is_high_risk=result.is_high_risk,
                        checked_at=datetime.now() - timedelta(days=2 - index),
                    )
                )

        if not db.scalar(select(Reminder).where(Reminder.owner_id == elderly.id)):
            db.add_all(
                [
                    Reminder(
                        owner_id=elderly.id,
                        created_by=family.id,
                        title="晚饭后服药",
                        reminder_type="medication",
                        due_at=datetime.now() + timedelta(hours=2),
                        recurrence="daily",
                        notes="遵医嘱使用，平台不提供剂量建议",
                    ),
                    Reminder(
                        owner_id=elderly.id,
                        created_by=elderly.id,
                        title="社区书法活动",
                        reminder_type="schedule",
                        due_at=datetime.now() + timedelta(days=2),
                        recurrence="weekly",
                    ),
                ]
            )

        if not db.scalar(select(EmergencyContact).where(EmergencyContact.owner_id == elderly.id)):
            db.add(
                EmergencyContact(
                    owner_id=elderly.id,
                    name="王小爱",
                    phone="13800000002",
                    relationship="女儿",
                    priority=1,
                )
            )
        db.commit()

    print("Demo data is ready.")
    print("Elderly: 13800000001 / Care1234")
    print("Family:  13800000002 / Care1234")


if __name__ == "__main__":
    main()
