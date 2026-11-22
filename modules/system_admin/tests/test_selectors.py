"""Selectors integration tests: queries, filtering, and dashboard aggregations."""
from datetime import UTC, date, datetime, timedelta

import pytest

from modules.system_admin.models.archive import ArchivedUserRecord
from modules.system_admin.models.audit import FailedLoginLog, SystemAuditLog
from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount
from modules.system_admin.selectors.archive_selectors import (
    get_archived_user,
    list_archived_users,
    list_historical_archives,
    list_purge_requests,
)
from modules.system_admin.selectors.audit_selectors import (
    get_system_parameters,
    list_audit_logs,
    list_failed_logins,
)
from modules.system_admin.selectors.dashboard_selectors import (
    get_system_admin_dashboard_metrics,
)
from modules.system_admin.selectors.role_selectors import (
    get_approaching_role_expiries,
    get_role_directory,
    list_role_assignments,
)
from modules.system_admin.selectors.user_selectors import (
    get_user_by_id,
    get_user_by_institute_id,
    list_users,
)

pytestmark = pytest.mark.django_db


def test_user_selectors():
    u = UserAccount.objects.create(
        user_id=5001,
        institute_id="2024BCS501",
        username="sel_user",
        email="sel@iiitdmj.ac.in",
        user_type="student",
        name="Selector User",
        department="CSE",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2024,
        status="active",
    )
    assert get_user_by_id(5001) == u
    assert get_user_by_institute_id("2024BCS501") == u
    assert get_user_by_id(9999) is None

    users, total = list_users(query="Selector", user_type="student", status="active")
    assert total >= 1
    assert any(x.user_id == 5001 for x in users)


def test_role_selectors():
    today = date.today()
    ra = RoleAssignment.objects.create(
        role_code="hod_cse",
        role_name="Head CSE",
        user_id=5001,
        status="active",
        is_singular=True,
        start_date=today,
        end_date=today + timedelta(days=15),  # within 30 days
        assigned_by=1,
    )
    results = list_role_assignments(user_id=5001, role_code="hod_cse")
    assert len(results) == 1
    assert results[0].id == ra.id

    directory = get_role_directory()
    hod_entry = next((e for e in directory if e["role_code"] == "hod_cse"), None)
    assert hod_entry is not None
    assert hod_entry["active_holders_count"] == 1
    assert not hod_entry["is_vacant"]

    expiring = get_approaching_role_expiries(within_days=30)
    assert any(x.id == ra.id for x in expiring)


def test_archive_selectors():
    now = datetime.now(UTC)
    ar = ArchivedUserRecord.objects.create(
        user_id=6001,
        institute_id="2024BCS601",
        username="arch_sel",
        email="arch.sel@iiitdmj.ac.in",
        user_type="student",
        reason="Graduated",
        retention_option="standard_7yr",
        archived_by=1,
        archived_at=now,
        reversible_until=now + timedelta(days=90),
    )
    assert get_archived_user(6001) == ar

    records, total = list_archived_users(query="arch_sel", user_type="student")
    assert total >= 1
    assert records[0].user_id == 6001


def test_dashboard_metrics():
    UserAccount.objects.create(
        user_id=7001,
        institute_id="2024BCS701",
        username="dash_user",
        email="dash@iiitdmj.ac.in",
        user_type="student",
        status="active",
    )
    SystemAuditLog.objects.create(
        actor_id=1,
        action="system_admin.test",
        result="success",
    )
    FailedLoginLog.objects.create(
        username="hacker",
        reason="Bad password",
    )

    metrics = get_system_admin_dashboard_metrics()
    assert metrics["users"]["total"] >= 1
    assert metrics["users"]["active"] >= 1
    assert metrics["security"]["failed_logins_24h"] >= 1
    assert metrics["system_health"]["status"] == "healthy"


def test_audit_and_config_selectors():
    now = datetime.now(UTC)
    SystemAuditLog.objects.create(
        actor_id=42,
        action="system_admin.test.filter",
        target_id="target42",
        result="success",
    )
    FailedLoginLog.objects.create(
        username="filter_attacker",
        reason="Invalid credentials",
    )

    logs, count = list_audit_logs(
        actor_id=42,
        action="test.filter",
        target_id="target42",
        result="success",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
    )
    assert count >= 1
    assert logs[0].actor_id == 42

    failed = list_failed_logins(username="filter_attacker")
    assert len(failed) >= 1
    assert failed[0].username == "filter_attacker"

    params = get_system_parameters()
    assert isinstance(params, dict)

    assert isinstance(list_historical_archives(), list)
    assert isinstance(list_purge_requests(), list)
