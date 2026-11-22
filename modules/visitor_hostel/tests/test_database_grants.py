"""Exercise the actual deployment grants in the disposable PostgreSQL test DB."""

from pathlib import Path

import pytest
from django.conf import settings
from django.db import DatabaseError, connection, transaction


@pytest.mark.django_db
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE vh_bill SET total_amount = 0",
        "DELETE FROM vh_bill",
        "UPDATE visitor_hostel_auditevent SET action = 'tampered'",
        "DELETE FROM visitor_hostel_auditevent",
        "UPDATE visitor_hostel_roleassignment SET user_id = 123",
        "CREATE TABLE unauthorized_table (id integer)",
    ],
)
def test_runtime_role_cannot_rewrite_history_or_grant_itself_access(statement):
    if connection.vendor != "postgresql":
        pytest.skip("Database privileges require PostgreSQL.")
    with connection.cursor() as cursor:
        cursor.execute((Path(settings.BASE_DIR) / "ops/db/roles.sql").read_text())
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE platform_app")
        cursor.execute(statement)


@pytest.mark.django_db
def test_runtime_role_can_read_bills_and_record_cash_settlement():
    if connection.vendor != "postgresql":
        pytest.skip("Database privileges require PostgreSQL.")
    with connection.cursor() as cursor:
        cursor.execute((Path(settings.BASE_DIR) / "ops/db/roles.sql").read_text())
        try:
            cursor.execute("SET LOCAL ROLE platform_app")
            cursor.execute("SELECT total_amount FROM vh_bill")
            cursor.execute("UPDATE vh_bill SET is_settled_offline = TRUE")
        finally:
            cursor.execute("RESET ROLE")
