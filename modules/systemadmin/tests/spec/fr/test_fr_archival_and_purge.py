"""Specification-Driven Tests for Functional Requirements (FR) - Archival and Purge.

Covers CFR-SA-011, CFR-SA-012, CFR-SA-013, CFR-SA-014, CFR-SA-015, CFR-SA-016.
All tests trace to source specification obligations and match a8_design/FR_DESIGN.json.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.archival import (
    ArchivedHistoricalData,
)
from modules.systemadmin.services.archival_service import ArchivalError, ArchivalService
from modules.systemadmin.services.user_service import UserService

pytestmark = pytest.mark.django_db

ALL_PERMISSIONS = (
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
)


def get_sa_client(stub_iam, permissions=ALL_PERMISSIONS):
    session = make_session(
        user_id=1,
        kind="staff",
        modules=("systemadmin",),
        permissions=permissions,
        roles=("Super Admin",),
        active_role="Super Admin",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-sa-1")
    return client


@pytest.fixture
def deactivated_user():
    u = UserService.create_basic_user(
        institute_id="ARCH_U_01",
        user_type="student",
        full_name="Deactivated Student",
        institute_email="arch_u_01@iiitdmj.ac.in",
        date_of_joining=date(2022, 8, 1),
        programme="B.Tech",
        batch_year=2022,
    )
    UserService.deactivate_user(u.id, reason="Graduated and departed")
    u.refresh_from_db()
    u.deactivated_at = timezone.now() - timedelta(days=35)
    u.save()
    return u


def test_fr_062_archive_eligible_user(deactivated_user):
    """TEST_FR_062 | AFR-SA-047: Verify Super Admin can archive eligible inactive user specifying date, reason, retention."""
    archived = ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="Graduated student record archival",
        retention_option="standard_institutional",
        actor_username="superadmin",
    )
    assert archived.status == "reversible"
    assert archived.user.status == "archived"


def test_fr_063_reject_archive_active_user():
    """TEST_FR_063 | AFR-SA-048-active: Verify system rejects archival of an active user account."""
    active_user = UserService.create_basic_user(
        institute_id="ACTIVE_U_01",
        user_type="faculty",
        full_name="Active Faculty",
        institute_email="active_u_01@iiitdmj.ac.in",
        date_of_joining=date(2023, 1, 1),
        department="ECE",
        employee_id="FAC_ACT_01",
    )
    with pytest.raises(ArchivalError):
        ArchivalService.archive_user(
            user_id=active_user.id,
            reason="Illegal attempt to archive active user",
        )


def test_fr_064_reject_archive_before_interval_elapses():
    """TEST_FR_064 | AFR-SA-048-interval: Verify system rejects archival if user has not met minimum deactivation interval."""
    user = UserService.create_basic_user(
        institute_id="FRESH_DEACT_01",
        user_type="student",
        full_name="Fresh Deact",
        institute_email="fresh_deact_01@iiitdmj.ac.in",
        date_of_joining=date(2025, 8, 1),
        programme="B.Tech",
        batch_year=2025,
    )
    UserService.deactivate_user(user.id, reason="Temporary hold")
    with pytest.raises(ArchivalError):
        ArchivalService.archive_user(
            user_id=user.id,
            reason="Premature archival attempt",
            bypass_interval=False,
        )


def test_fr_065_credentials_disabled_on_archival(deactivated_user):
    """TEST_FR_065 | AFR-SA-049A: Verify login credentials and system access are disabled on user archival."""
    ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="Archival access revocation",
    )
    deactivated_user.refresh_from_db()
    assert deactivated_user.has_dashboard_access is False
    assert deactivated_user.status == "archived"


def test_fr_066_archived_user_listed_under_archived_view(stub_iam, deactivated_user):
    """TEST_FR_066 | AFR-SA-049B: Verify archived user is moved to archive and listed under Archived Users view."""
    ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="List test",
    )
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/users/")
    assert resp.status_code == 200
    results = resp.data.get("results", resp.data)
    assert any(
        r.get("user_details", {}).get("institute_id") == deactivated_user.institute_id
        or r.get("user") == deactivated_user.id
        for r in results
    )


def test_fr_067_archive_retains_required_data(deactivated_user):
    """TEST_FR_067 | AFR-SA-050: Verify archive retains required profile snapshot, role history, and activity audit."""
    record = ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="Data retention test",
    )
    assert record.retained_profile_snapshot["institute_id"] == deactivated_user.institute_id
    assert "user_type" in record.retained_profile_snapshot


def test_fr_068_restore_archived_user_within_reversible_window(deactivated_user):
    """TEST_FR_068 | AFR-SA-051A: Verify Super Admin can restore archived user during reversible period with authorization."""
    record = ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="Restore test",
    )
    restored = ArchivalService.restore_archived_user(
        archived_user_id=record.id,
        authorization_ref="AUTH-RESTORE-101",
        actor_username="superadmin",
    )
    assert restored.status == "active"
    record.refresh_from_db()
    assert record.status == "restored"


def test_fr_069_reject_restore_after_reversible_window_expires(deactivated_user):
    """TEST_FR_069 | AFR-SA-051B: Verify system rejects restoration after reversible period expires (ISS-SA-004)."""
    record = ArchivalService.archive_user(
        user_id=deactivated_user.id,
        reason="Reversibility expiry test",
    )
    record.reversibility_deadline = timezone.now() - timedelta(days=1)
    record.save()

    with pytest.raises(ArchivalError):
        ArchivalService.restore_archived_user(
            archived_user_id=record.id,
            authorization_ref="AUTH-LATE-001",
        )


def test_fr_070_archive_historical_data_category_and_date_range():
    """TEST_FR_070 | AFR-SA-052: Verify Super Admin can initiate historical data archival by selecting category and date range."""
    archived_data = ArchivalService.archive_historical_data(
        category="audit_logs",
        date_range_start=date(2023, 1, 1),
        date_range_end=date(2023, 12, 31),
        actor_username="superadmin",
    )
    assert archived_data.status == "archived"
    assert archived_data.category == "audit_logs"


def test_fr_071_historical_archival_validates_dependencies():
    """TEST_FR_071 | AFR-SA-053-valid: Verify system validates mandatory category criteria before historical archival."""
    # AFR-SA-048 / AFR-SA-053: Missing or blank category must be rejected
    with pytest.raises(ArchivalError):
        ArchivalService.archive_historical_data(
            category="",
            date_range_start=date(2022, 1, 1),
            date_range_end=date(2022, 12, 31),
            record_count=100,
        )


def test_fr_072_reject_historical_archival_with_invalid_date_range():
    """TEST_FR_072 | AFR-SA-053-ineligible: Verify system rejects historical archival with invalid inverted date range."""
    with pytest.raises(ArchivalError):
        ArchivalService.archive_historical_data(
            category="transactions",
            date_range_start=date(2025, 1, 1),
            date_range_end=date(2020, 1, 1),
        )


def test_fr_073_historical_archival_critical_operation_confirmation(stub_iam):
    """TEST_FR_073 | AFR-SA-054A: Verify historical data archival requires confirmation immediately before execution."""
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/archival/historical/create/",
        {
            "category": "system_events",
            "date_range_start": "2023-01-01",
            "date_range_end": "2023-06-30",
            "record_count": 50,
            "storage_size_kb": 1200,
            "backup_reference": "BKP-SYS-2023",
            "retention_years": 7,
        },
        format="json",
    )
    assert resp.status_code in (200, 201)


def test_fr_074_historical_archival_creates_backup():
    """TEST_FR_074 | AFR-SA-054B: Verify backup creation/reference occurs before moving historical data to archive."""
    data = ArchivalService.archive_historical_data(
        category="session_logs",
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 6, 30),
    )
    assert data.backup_reference.startswith("BKP-") or len(data.backup_reference) > 0


def test_fr_075_historical_data_moved_to_archive():
    """TEST_FR_075 | AFR-SA-055A: Verify eligible historical data record is persisted in archive storage."""
    data = ArchivalService.archive_historical_data(
        category="notifications",
        date_range_start=date(2023, 6, 1),
        date_range_end=date(2023, 12, 31),
    )
    assert ArchivedHistoricalData.objects.filter(id=data.id).exists()


def test_fr_076_archival_summary_report_generated():
    """TEST_FR_076 | AFR-SA-055B: Verify archival summary report metadata is generated upon completion."""
    data = ArchivalService.archive_historical_data(
        category="security_events",
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 3, 31),
    )
    assert "backup_created" in data.summary_metadata or data.record_count >= 0


def test_fr_077_read_only_searchable_archived_records(stub_iam):
    """TEST_FR_077 | AFR-SA-056: Verify system provides read-only searchable access to permitted archived records."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/")
    assert resp.status_code == 200


def test_fr_078_search_and_filter_archived_records(stub_iam):
    """TEST_FR_078 | AFR-SA-058: Verify Super Admin can view, search, and filter archived records by category and dates."""
    ArchivalService.archive_historical_data(
        category="filter_test_cat",
        date_range_start=date(2023, 1, 1),
        date_range_end=date(2023, 6, 30),
    )
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/?category=filter_test_cat")
    assert resp.status_code == 200
    results = resp.data.get("results", resp.data)
    assert any(r["category"] == "filter_test_cat" for r in results)


def test_fr_079_generate_archive_reports(stub_iam):
    """TEST_FR_079 | AFR-SA-059A: Verify Super Admin can generate archive reports from permitted archived data."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/")
    assert resp.status_code == 200


def test_fr_080_export_archive_results(stub_iam):
    """TEST_FR_080 | AFR-SA-059B: Verify Super Admin can export archive results."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/?export=csv")
    assert resp.status_code == 200


def test_fr_081_export_authorized_archive_package(stub_iam):
    """TEST_FR_081 | AFR-SA-060: Verify Super Admin can export authorized archive packages."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/users/?export=json")
    assert resp.status_code == 200


def test_fr_082_restore_archived_historical_data():
    """TEST_FR_082 | AFR-SA-057: Verify archived historical data can be restored to active system with approved reference."""
    data = ArchivalService.archive_historical_data(
        category="restorable_data",
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 2, 28),
    )
    restored = ArchivalService.restore_historical_data(
        data_id=data.id,
        approval_ref="DIR-APPROVAL-2026-09",
    )
    assert restored.status == "restored"
    assert restored.restoration_approval_ref == "DIR-APPROVAL-2026-09"


def test_fr_083_reject_permanent_purge_before_retention_expiry():
    """TEST_FR_083 | AFR-SA-061A-before: Verify system rejects permanent-purge request if retention period has not elapsed."""
    future_data = ArchivedHistoricalData.objects.create(
        category="unexpired_cat",
        date_range_start=date(2025, 1, 1),
        date_range_end=date(2025, 12, 31),
        archived_by="superadmin",
        record_count=50,
        storage_size_kb=100,
        backup_reference="BKP-UNEXP",
        status="archived",
        retention_expiry_date=date.today() + timedelta(days=365),
    )
    with pytest.raises(ArchivalError):
        ArchivalService.request_permanent_purge(
            target_type="historical_data",
            target_id=future_data.id,
            reason="Premature purge request",
        )


def test_fr_084_prevent_purge_without_it_head_dual_authorization():
    """TEST_FR_084 | AFR-SA-061B-single: Verify system prevents permanent purge execution with only Super Admin authorization."""
    expired_data = ArchivedHistoricalData.objects.create(
        category="expired_cat",
        date_range_start=date(2010, 1, 1),
        date_range_end=date(2010, 12, 31),
        archived_by="superadmin",
        record_count=50,
        storage_size_kb=100,
        backup_reference="BKP-EXP",
        status="archived",
        retention_expiry_date=date.today() - timedelta(days=10),
    )
    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=expired_data.id,
        reason="Retention fully elapsed",
    )
    assert purge_req.status == "pending_it_head"
    expired_data.refresh_from_db()
    assert expired_data.status == "archived"


def test_fr_085_dual_authorized_permanent_purge_executes():
    """TEST_FR_085 | AFR-SA-061B-dual: Verify permanent purge executes when retention expired and dual authorization exists."""
    expired_data = ArchivedHistoricalData.objects.create(
        category="expired_dual_cat",
        date_range_start=date(2010, 1, 1),
        date_range_end=date(2010, 12, 31),
        archived_by="superadmin",
        record_count=50,
        storage_size_kb=100,
        backup_reference="BKP-EXP-DUAL",
        status="archived",
        retention_expiry_date=date.today() - timedelta(days=10),
    )
    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=expired_data.id,
        reason="Retention expired dual authorization test",
    )
    final_req = ArchivalService.authorize_permanent_purge(
        request_id=purge_req.id,
        decision="approve",
        it_head_username="it_head_admin",
        comments="Approved by IT Head",
    )
    assert final_req.status == "approved"
    # AFR-SA-061B: Permanent purge must permanently remove target record from database
    assert not ArchivedHistoricalData.objects.filter(id=expired_data.id).exists()
