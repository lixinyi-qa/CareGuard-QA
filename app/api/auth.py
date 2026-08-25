from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, mask_phone, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        phone_masked=mask_phone(user.phone),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    if db.scalar(select(User).where(User.phone == payload.phone)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PHONE_EXISTS", "message": "该手机号已注册"},
        )
    user = User(
        name=payload.name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        consent_version="2026-01",
    )
    db.add(user)
    db.flush()
    write_audit(db, actor_id=user.id, action="register", resource_type="user", resource_id=user.id)
    db.commit()
    token, expires_in = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=expires_in, user=to_user_read(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None or not verify_password(payload.password, user.password_hash):
        write_audit(
            db,
            actor_id=user.id if user else None,
            action="login",
            resource_type="session",
            outcome="denied",
            detail="invalid_credentials",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "手机号或密码错误"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DISABLED", "message": "账号已停用"},
        )
    write_audit(db, actor_id=user.id, action="login", resource_type="session")
    db.commit()
    token, expires_in = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=expires_in, user=to_user_read(user))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return to_user_read(user)
