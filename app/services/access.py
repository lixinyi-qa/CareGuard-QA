from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import CareLink, User


def has_active_care_link(db: Session, user: User, elderly_id: int) -> bool:
    if user.id == elderly_id:
        return True
    if user.role == "admin":
        return True
    if user.role != "family":
        return False
    link = db.scalar(
        select(CareLink).where(
            CareLink.elderly_id == elderly_id,
            CareLink.family_id == user.id,
            CareLink.status == "active",
        )
    )
    return link is not None


def linked_user_ids(db: Session, user: User) -> set[int]:
    if user.role == "elderly":
        return {user.id}
    if user.role == "admin":
        return set(db.scalars(select(User.id)).all())
    return set(
        db.scalars(
            select(CareLink.elderly_id).where(
                CareLink.family_id == user.id, CareLink.status == "active"
            )
        ).all()
    )


def visible_link_filter(user: User):
    return or_(CareLink.elderly_id == user.id, CareLink.family_id == user.id)
