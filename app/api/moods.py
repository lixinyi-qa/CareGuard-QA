from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession
from app.models import Alert, MoodCheckin
from app.schemas.mood import MoodCreate, MoodRead, MoodStats
from app.services.access import has_active_care_link
from app.services.audit import write_audit
from app.services.emotion import DISCLAIMER, classify_emotion, emotion_display

router = APIRouter(prefix="/moods", tags=["Mood check-ins"])


def to_mood_read(mood: MoodCheckin, *, include_text: bool) -> MoodRead:
    return MoodRead(
        id=mood.id,
        user_id=mood.user_id,
        text=mood.text if include_text else None,
        emotion=mood.emotion,
        emotion_display=emotion_display(mood.emotion),
        confidence=mood.confidence,
        is_high_risk=mood.is_high_risk,
        checked_at=mood.checked_at,
        disclaimer=DISCLAIMER,
    )


@router.post("", response_model=MoodRead, status_code=status.HTTP_201_CREATED)
def create_mood(payload: MoodCreate, db: DbSession, user: CurrentUser) -> MoodRead:
    if user.role != "elderly":
        raise HTTPException(
            status_code=403,
            detail={"code": "ELDERLY_ONLY", "message": "只有老人账号可以进行情绪打卡"},
        )
    result = classify_emotion(payload.text)
    mood = MoodCheckin(
        user_id=user.id,
        text=payload.text,
        emotion=result.label,
        confidence=result.confidence,
        is_high_risk=result.is_high_risk,
    )
    db.add(mood)
    db.flush()

    if result.is_high_risk:
        db.add(
            Alert(
                owner_id=user.id,
                alert_type="wellbeing_attention",
                severity="high",
                message="检测到需要优先关怀的表达，请家属尽快通过电话或当面确认安全。紧急情况请联系当地急救服务。",
                source_mood_id=mood.id,
            )
        )
    elif result.label == "negative":
        recent = db.scalars(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == user.id)
            .order_by(MoodCheckin.checked_at.desc(), MoodCheckin.id.desc())
            .limit(3)
        ).all()
        if len(recent) == 3 and all(item.emotion == "negative" for item in recent):
            already_open = db.scalar(
                select(Alert).where(
                    Alert.owner_id == user.id,
                    Alert.alert_type == "negative_streak",
                    Alert.status == "open",
                    Alert.created_at >= datetime.now() - timedelta(days=7),
                )
            )
            if not already_open:
                db.add(
                    Alert(
                        owner_id=user.id,
                        alert_type="negative_streak",
                        severity="medium",
                        message="近期连续出现消极情绪记录，建议家属主动问候并关注日常状态。",
                        source_mood_id=mood.id,
                    )
                )

    write_audit(db, actor_id=user.id, action="create", resource_type="mood", resource_id=mood.id)
    db.commit()
    return to_mood_read(mood, include_text=True)


@router.get("", response_model=list[MoodRead])
def list_moods(
    db: DbSession,
    user: CurrentUser,
    owner_id: int | None = None,
    limit: int = Query(default=30, ge=1, le=100),
) -> list[MoodRead]:
    target_id = owner_id or user.id
    if not has_active_care_link(db, user, target_id):
        write_audit(
            db,
            actor_id=user.id,
            action="read",
            resource_type="mood",
            resource_id=target_id,
            outcome="denied",
            detail="care_link_required",
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail={"code": "MOOD_FORBIDDEN", "message": "无权查看该用户的情绪记录"},
        )
    moods = db.scalars(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == target_id)
        .order_by(MoodCheckin.checked_at.desc(), MoodCheckin.id.desc())
        .limit(limit)
    ).all()
    include_text = target_id == user.id or user.role == "admin"
    return [to_mood_read(item, include_text=include_text) for item in moods]


@router.get("/stats", response_model=MoodStats)
def mood_stats(
    db: DbSession, user: CurrentUser, owner_id: int | None = None, days: int = Query(30, ge=1, le=365)
) -> MoodStats:
    target_id = owner_id or user.id
    if not has_active_care_link(db, user, target_id):
        raise HTTPException(status_code=403, detail={"code": "MOOD_FORBIDDEN", "message": "无权查看该用户的情绪统计"})
    since = datetime.now() - timedelta(days=days)
    rows = db.execute(
        select(MoodCheckin.emotion, func.count(MoodCheckin.id))
        .where(MoodCheckin.user_id == target_id, MoodCheckin.checked_at >= since)
        .group_by(MoodCheckin.emotion)
    ).all()
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    counts.update({emotion: count for emotion, count in rows})
    latest = db.scalar(
        select(MoodCheckin.emotion)
        .where(MoodCheckin.user_id == target_id)
        .order_by(MoodCheckin.checked_at.desc(), MoodCheckin.id.desc())
        .limit(1)
    )
    return MoodStats(
        **counts,
        total=sum(counts.values()),
        latest_emotion=latest,
        disclaimer=DISCLAIMER,
    )
