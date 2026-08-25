import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import Base, engine

pytestmark = pytest.mark.mysql


def require_mysql() -> None:
    if os.getenv("RUN_MYSQL_TESTS") != "1":
        pytest.skip("Set RUN_MYSQL_TESTS=1 with a dedicated MySQL database")


def test_mysql_connection_version_and_utf8mb4_schema():
    require_mysql()
    assert engine.dialect.name == "mysql"
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        version = connection.execute(text("SELECT VERSION()")).scalar_one()
        charset = connection.execute(
            text(
                "SELECT DEFAULT_CHARACTER_SET_NAME FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = DATABASE()"
            )
        ).scalar_one()
    major, minor = (int(part) for part in version.split("-", 1)[0].split(".")[:2])
    assert (major, minor) >= (8, 4)
    assert charset == "utf8mb4"
    assert "mood_checkins" in inspect(engine).get_table_names()


def test_mysql_tables_use_innodb_and_utf8mb4():
    require_mysql()
    Base.metadata.create_all(engine)
    expected_tables = {
        "alerts",
        "audit_logs",
        "care_links",
        "emergency_contacts",
        "mood_checkins",
        "reminders",
        "users",
    }
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION "
                "FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
            )
        ).mappings()
        table_contract = {row["TABLE_NAME"]: row for row in rows}

    assert expected_tables.issubset(table_contract)
    for table_name in expected_tables:
        assert table_contract[table_name]["ENGINE"].lower() == "innodb"
        assert table_contract[table_name]["TABLE_COLLATION"].startswith("utf8mb4")


def test_mysql_foreign_keys_and_unique_constraints_exist():
    require_mysql()
    Base.metadata.create_all(engine)
    schema = inspect(engine)
    assert {item["referred_table"] for item in schema.get_foreign_keys("care_links")} == {
        "users"
    }
    assert {item["referred_table"] for item in schema.get_foreign_keys("reminders")} == {
        "users"
    }
    user_unique_columns = {
        tuple(item["column_names"]) for item in schema.get_unique_constraints("users")
    }
    assert ("phone",) in user_unique_columns
    care_link_unique_columns = {
        tuple(item["column_names"])
        for item in schema.get_unique_constraints("care_links")
    }
    assert ("elderly_id", "family_id") in care_link_unique_columns


def test_mysql_chinese_unicode_round_trip_is_rollback_safe():
    require_mysql()
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(name, phone, password_hash, role, is_active, consent_version) "
                    "VALUES (:name, :phone, :password_hash, 'elderly', 1, '2026-01')"
                ),
                {
                    "name": "测试老人🙂",
                    "phone": "13899990001",
                    "password_hash": "integration-test-only",
                },
            )
            stored_name = connection.execute(
                text("SELECT name FROM users WHERE phone = '13899990001'")
            ).scalar_one()
            assert stored_name == "测试老人🙂"
        finally:
            transaction.rollback()

    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM users WHERE phone = '13899990001'")
            ).scalar_one()
            == 0
        )


def test_mysql_rejects_orphan_foreign_key_rows():
    require_mysql()
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO mood_checkins "
                        "(user_id, text, emotion, confidence, is_high_risk) "
                        "VALUES (999999999, '孤儿数据', 'neutral', 50, 0)"
                    )
                )
        finally:
            transaction.rollback()
