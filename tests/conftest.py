from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)
PASSWORD = "Care1234"
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(TEST_ENGINE)
    session = TestSession()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture()
def client(db: Session) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def users(db: Session) -> dict[str, User]:
    created = {
        "elderly": User(
            name="王安心", phone="13800000001", password_hash=PASSWORD_HASH, role="elderly"
        ),
        "family": User(
            name="王小爱", phone="13800000002", password_hash=PASSWORD_HASH, role="family"
        ),
        "outsider": User(
            name="李家属", phone="13800000003", password_hash=PASSWORD_HASH, role="family"
        ),
    }
    db.add_all(created.values())
    db.commit()
    return created


@pytest.fixture()
def headers(users: dict[str, User]) -> dict[str, dict[str, str]]:
    result = {}
    for key, user in users.items():
        token, _ = create_access_token(user.id, user.role)
        result[key] = {"Authorization": f"Bearer {token}"}
    return result
