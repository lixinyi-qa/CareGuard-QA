from sqlalchemy import inspect


def test_required_tables_are_created(db):
    tables = set(inspect(db.bind).get_table_names())
    assert {
        "users",
        "care_links",
        "mood_checkins",
        "reminders",
        "emergency_contacts",
        "alerts",
        "audit_logs",
    }.issubset(tables)


def test_phone_column_has_unique_constraint(db):
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes("users")
    unique_constraints = inspector.get_unique_constraints("users")
    assert any(index["unique"] and index["column_names"] == ["phone"] for index in indexes) or any(
        item["column_names"] == ["phone"] for item in unique_constraints
    )
