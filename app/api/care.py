from datetime import datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.security import mask_name, mask_phone
from app.models import CareLink, EmergencyContact, User
from app.schemas.care import CareLinkCreate, CareLinkRead, ContactCreate, ContactRead
from app.services.access import has_active_care_link, visible_link_filter
from app.services.audit import write_audit

router = APIRouter(tags=["Care relationships"])


def to_link_read(link: CareLink) -> CareLinkRead:
    return CareLinkRead(
        id=link.id,
        elderly_id=link.elderly_id,
        family_id=link.family_id,
        elderly_name=link.elderly.name,
        family_name=link.family.name,
        status=link.status,
        created_at=link.created_at,
        accepted_at=link.accepted_at,
    )


@router.post("/care-links", response_model=CareLinkRead, status_code=status.HTTP_201_CREATED)
def create_link(payload: CareLinkCreate, db: DbSession, user: CurrentUser) -> CareLinkRead:
    if user.role != "family":
        raise HTTPException(
            status_code=403,
            detail={"code": "FAMILY_ONLY", "message": "只有家属账号可以发起绑定"},
        )
    elderly = db.scalar(select(User).where(User.phone == payload.elderly_phone))
    if elderly is None or elderly.role != "elderly":
        raise HTTPException(
            status_code=404,
            detail={"code": "ELDERLY_NOT_FOUND", "message": "未找到对应老人账号"},
        )
    existing = db.scalar(
        select(CareLink).where(
            CareLink.elderly_id == elderly.id, CareLink.family_id == user.id
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "LINK_EXISTS", "message": "绑定关系已存在"},
        )
    link = CareLink(elderly_id=elderly.id, family_id=user.id, status="pending")
    db.add(link)
    db.flush()
    write_audit(db, actor_id=user.id, action="invite", resource_type="care_link", resource_id=link.id)
    db.commit()
    return to_link_read(link)


@router.get("/care-links", response_model=list[CareLinkRead])
def list_links(db: DbSession, user: CurrentUser) -> list[CareLinkRead]:
    links = db.scalars(select(CareLink).where(visible_link_filter(user)).order_by(CareLink.id.desc())).all()
    return [to_link_read(link) for link in links]


@router.post("/care-links/{link_id}/accept", response_model=CareLinkRead)
def accept_link(link_id: int, db: DbSession, user: CurrentUser) -> CareLinkRead:
    link = db.get(CareLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail={"code": "LINK_NOT_FOUND", "message": "绑定邀请不存在"})
    if user.role != "elderly" or link.elderly_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "LINK_FORBIDDEN", "message": "只能由受邀老人确认绑定"})
    if link.status != "pending":
        raise HTTPException(status_code=409, detail={"code": "LINK_NOT_PENDING", "message": "该邀请不是待确认状态"})
    link.status = "active"
    link.accepted_at = datetime.now()
    write_audit(db, actor_id=user.id, action="accept", resource_type="care_link", resource_id=link.id)
    db.commit()
    return to_link_read(link)


@router.delete("/care-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_link(link_id: int, db: DbSession, user: CurrentUser) -> Response:
    link = db.get(CareLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail={"code": "LINK_NOT_FOUND", "message": "绑定关系不存在"})
    if user.id not in {link.elderly_id, link.family_id} and user.role != "admin":
        raise HTTPException(status_code=403, detail={"code": "LINK_FORBIDDEN", "message": "无权解除该绑定"})
    link.status = "revoked"
    write_audit(db, actor_id=user.id, action="revoke", resource_type="care_link", resource_id=link.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/contacts", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, db: DbSession, user: CurrentUser) -> ContactRead:
    owner_id = payload.owner_id or user.id
    owner = db.get(User, owner_id)
    if owner is None or owner.role != "elderly":
        raise HTTPException(status_code=404, detail={"code": "OWNER_NOT_FOUND", "message": "老人账号不存在"})
    if not has_active_care_link(db, user, owner_id):
        raise HTTPException(status_code=403, detail={"code": "CONTACT_FORBIDDEN", "message": "无权维护该联系人"})
    contact = EmergencyContact(
        owner_id=owner_id,
        name=payload.name,
        phone=payload.phone,
        relationship=payload.relationship,
        priority=payload.priority,
    )
    db.add(contact)
    db.flush()
    write_audit(db, actor_id=user.id, action="create", resource_type="contact", resource_id=contact.id)
    db.commit()
    return _contact_read(contact)


def _contact_read(contact: EmergencyContact) -> ContactRead:
    return ContactRead(
        id=contact.id,
        owner_id=contact.owner_id,
        name_masked=mask_name(contact.name),
        phone_masked=mask_phone(contact.phone),
        relationship=contact.relationship,
        priority=contact.priority,
        created_at=contact.created_at,
    )


@router.get("/contacts", response_model=list[ContactRead])
def list_contacts(db: DbSession, user: CurrentUser, owner_id: int | None = None) -> list[ContactRead]:
    target_id = owner_id or user.id
    if not has_active_care_link(db, user, target_id):
        raise HTTPException(status_code=403, detail={"code": "CONTACT_FORBIDDEN", "message": "无权查看该联系人"})
    contacts = db.scalars(
        select(EmergencyContact)
        .where(EmergencyContact.owner_id == target_id)
        .order_by(EmergencyContact.priority, EmergencyContact.id)
    ).all()
    return [_contact_read(item) for item in contacts]
