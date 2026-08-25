from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Alert, CareLink, User


def activate_link(db, users) -> CareLink:
    link = CareLink(
        elderly_id=users["elderly"].id,
        family_id=users["family"].id,
        status="active",
        accepted_at=datetime.now(),
    )
    db.add(link)
    db.commit()
    return link


def create_mood(client, headers, text="今天很开心"):
    return client.post("/api/v1/moods", headers=headers["elderly"], json={"text": text})


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


def test_register_success_returns_masked_profile(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "赵奶奶",
            "phone": "13900000009",
            "password": "Hello123",
            "role": "elderly",
            "consent": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["phone_masked"] == "139****0009"
    assert "password" not in str(body).lower()


def test_register_rejects_duplicate_phone(client, users):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "重复用户",
            "phone": users["elderly"].phone,
            "password": "Hello123",
            "role": "elderly",
            "consent": True,
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "PHONE_EXISTS"


@pytest.mark.parametrize(
    "patch",
    [
        {"password": "onlyletters"},
        {"password": "12345678"},
        {"consent": False},
        {"phone": "123"},
    ],
)
def test_register_validates_security_fields(client, patch):
    payload = {
        "name": "校验用户",
        "phone": "13900000008",
        "password": "Hello123",
        "role": "elderly",
        "consent": True,
    }
    payload.update(patch)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_login_success(client, users):
    response = client.post(
        "/api/v1/auth/login", json={"phone": users["elderly"].phone, "password": "Care1234"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "elderly"


def test_login_failure_has_generic_message(client, users):
    response = client.post(
        "/api/v1/auth/login", json={"phone": users["elderly"].phone, "password": "Wrong123"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert users["elderly"].phone not in response.text


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_me_never_exposes_full_phone(client, users, headers):
    response = client.get("/api/v1/auth/me", headers=headers["elderly"])
    assert response.status_code == 200
    assert users["elderly"].phone not in response.text


def test_family_can_send_link_invitation(client, users, headers):
    response = client.post(
        "/api/v1/care-links",
        headers=headers["family"],
        json={"elderly_phone": users["elderly"].phone},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_elderly_cannot_send_link_invitation(client, users, headers):
    response = client.post(
        "/api/v1/care-links",
        headers=headers["elderly"],
        json={"elderly_phone": users["elderly"].phone},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FAMILY_ONLY"


def test_elderly_accepts_own_link_invitation(client, db, users, headers):
    link = CareLink(elderly_id=users["elderly"].id, family_id=users["family"].id)
    db.add(link)
    db.commit()
    response = client.post(f"/api/v1/care-links/{link.id}/accept", headers=headers["elderly"])
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_outsider_cannot_accept_link_invitation(client, db, users, headers):
    link = CareLink(elderly_id=users["elderly"].id, family_id=users["family"].id)
    db.add(link)
    db.commit()
    response = client.post(f"/api/v1/care-links/{link.id}/accept", headers=headers["outsider"])
    assert response.status_code == 403


def test_duplicate_link_is_rejected(client, db, users, headers):
    activate_link(db, users)
    response = client.post(
        "/api/v1/care-links",
        headers=headers["family"],
        json={"elderly_phone": users["elderly"].phone},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "LINK_EXISTS"


def test_link_member_can_revoke_access(client, db, users, headers):
    link = activate_link(db, users)
    response = client.delete(f"/api/v1/care-links/{link.id}", headers=headers["elderly"])
    assert response.status_code == 204
    db.refresh(link)
    assert link.status == "revoked"


@pytest.mark.parametrize(
    ("text", "emotion"),
    [
        ("今天阳光很好，我很开心", "positive"),
        ("今天在家看了电视", "neutral"),
        ("晚上失眠，我很难过", "negative"),
    ],
)
def test_elderly_creates_three_class_mood(client, users, headers, text, emotion):
    response = create_mood(client, headers, text)
    assert response.status_code == 201
    assert response.json()["emotion"] == emotion
    assert "不构成医疗诊断" in response.json()["disclaimer"]


def test_family_cannot_create_mood_for_elderly(client, users, headers):
    response = client.post(
        "/api/v1/moods", headers=headers["family"], json={"text": "替老人打卡"}
    )
    assert response.status_code == 403


def test_unlinked_family_cannot_read_moods(client, users, headers):
    create_mood(client, headers)
    response = client.get(
        f"/api/v1/moods?owner_id={users['elderly'].id}", headers=headers["family"]
    )
    assert response.status_code == 403
    assert response.json()["code"] == "MOOD_FORBIDDEN"


def test_linked_family_sees_label_but_not_raw_text(client, db, users, headers):
    activate_link(db, users)
    private_text = "今天想起了一件只想自己知道的事情"
    create_mood(client, headers, private_text)
    response = client.get(
        f"/api/v1/moods?owner_id={users['elderly'].id}", headers=headers["family"]
    )
    assert response.status_code == 200
    assert response.json()[0]["text"] is None
    assert private_text not in response.text


def test_owner_can_read_own_raw_mood_text(client, users, headers):
    private_text = "今天和朋友喝茶很开心"
    create_mood(client, headers, private_text)
    response = client.get("/api/v1/moods", headers=headers["elderly"])
    assert response.json()[0]["text"] == private_text


def test_three_negative_checkins_create_one_streak_alert(client, db, users, headers):
    for text in ("今天很难过", "昨晚失眠很焦虑", "一个人很孤独"):
        assert create_mood(client, headers, text).status_code == 201
    alerts = db.scalars(select(Alert).where(Alert.alert_type == "negative_streak")).all()
    assert len(alerts) == 1
    assert alerts[0].severity == "medium"


def test_high_risk_checkin_creates_generic_alert_without_leaking_text(client, db, users, headers):
    raw_text = "我不想活了"
    response = create_mood(client, headers, raw_text)
    assert response.json()["is_high_risk"] is True
    alert = db.scalar(select(Alert).where(Alert.alert_type == "wellbeing_attention"))
    assert alert is not None
    assert raw_text not in alert.message
    assert "诊断" not in alert.message


def test_mood_stats_are_aggregated(client, users, headers):
    create_mood(client, headers, "今天很开心")
    create_mood(client, headers, "今天在家吃饭")
    response = client.get("/api/v1/moods/stats", headers=headers["elderly"])
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["positive"] == 1


def test_elderly_creates_reminder(client, users, headers):
    due = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    response = client.post(
        "/api/v1/reminders",
        headers=headers["elderly"],
        json={"title": "晚饭后服药", "reminder_type": "medication", "due_at": due},
    )
    assert response.status_code == 201
    assert response.json()["owner_id"] == users["elderly"].id


def test_unlinked_family_cannot_create_reminder(client, users, headers):
    response = client.post(
        "/api/v1/reminders",
        headers=headers["family"],
        json={
            "owner_id": users["elderly"].id,
            "title": "体检",
            "reminder_type": "schedule",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 403


def test_linked_family_can_create_reminder(client, db, users, headers):
    activate_link(db, users)
    response = client.post(
        "/api/v1/reminders",
        headers=headers["family"],
        json={
            "owner_id": users["elderly"].id,
            "title": "社区活动",
            "reminder_type": "schedule",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "recurrence": "weekly",
        },
    )
    assert response.status_code == 201
    assert response.json()["created_by"] == users["family"].id


def test_reminder_can_be_completed(client, users, headers):
    created = client.post(
        "/api/v1/reminders",
        headers=headers["elderly"],
        json={
            "title": "喝水",
            "reminder_type": "schedule",
            "due_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
    ).json()
    response = client.patch(
        f"/api/v1/reminders/{created['id']}",
        headers=headers["elderly"],
        json={"is_completed": True},
    )
    assert response.status_code == 200
    assert response.json()["is_completed"] is True


def test_reminder_delete_and_not_found(client, users, headers):
    response = client.delete("/api/v1/reminders/9999", headers=headers["elderly"])
    assert response.status_code == 404
    assert response.json()["code"] == "REMINDER_NOT_FOUND"


def test_contact_is_masked_in_response(client, users, headers):
    response = client.post(
        "/api/v1/contacts",
        headers=headers["elderly"],
        json={"name": "王小爱", "phone": "13912345678", "relationship": "女儿", "priority": 1},
    )
    assert response.status_code == 201
    assert response.json()["phone_masked"] == "139****5678"
    assert response.json()["name_masked"] == "王**"
    assert "13912345678" not in response.text


def test_unlinked_family_cannot_read_contacts(client, users, headers):
    response = client.get(
        f"/api/v1/contacts?owner_id={users['elderly'].id}", headers=headers["family"]
    )
    assert response.status_code == 403


def test_alert_can_be_acknowledged_once(client, db, users, headers):
    activate_link(db, users)
    create_mood(client, headers, "我觉得活着没意思")
    alert = db.scalar(select(Alert))
    first = client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=headers["family"])
    second = client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=headers["family"])
    assert first.status_code == 200
    assert first.json()["status"] == "acknowledged"
    assert second.status_code == 409


def test_privacy_export_contains_only_current_users_data(client, users, headers):
    create_mood(client, headers, "今天很开心")
    response = client.get("/api/v1/privacy/export", headers=headers["elderly"])
    assert response.status_code == 200
    assert response.json()["user"]["id"] == users["elderly"].id
    assert len(response.json()["moods"]) == 1


def test_user_can_read_own_audit_log(client, users, headers):
    create_mood(client, headers)
    response = client.get("/api/v1/audit-logs/me", headers=headers["elderly"])
    assert response.status_code == 200
    assert any(item["resource_type"] == "mood" for item in response.json())


def test_ai_model_card_states_scope_and_limitations(client):
    response = client.get("/api/v1/ai/model-card")
    assert response.status_code == 200
    body = response.json()
    assert body["labels"] == ["positive", "neutral", "negative"]
    assert "medical diagnosis" in body["out_of_scope"]
    assert body["known_limitations"]


def test_security_headers_are_present(client):
    response = client.get("/health", headers={"X-Request-ID": "qa-correlation-001"})
    assert response.headers["x-request-id"] == "qa-correlation-001"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src" in response.headers["content-security-policy"]
