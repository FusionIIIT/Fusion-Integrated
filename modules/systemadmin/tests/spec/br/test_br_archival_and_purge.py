"""BR Test Suite 3: Archival, Reversibility, Backups, and Permanent Purge (BR-SA-004..005, 017..022)."""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models import (
    ArchivedHistoricalData,
    BasicUserProfile,
)
from modules.systemadmin.services.archival_service import ArchivalError, ArchivalService
from modules.systemadmin.services.user_service import UserService

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


def ensure_test_user(iid, utype="faculty", dept="CSE"):
    u = BasicUserProfile.objects.filter(institute_id=iid).first()
    if not u:
        kw = {
            "institute_id": iid,
            "user_type": utype,
            "full_name": f"User {iid}",
            "institute_email": f"{iid.lower()}@iiitdmj.ac.in",
            "date_of_joining": date(2024, 1, 1),
            "department": dept,
        }
        if utype == "student":
            kw["programme"] = "B.Tech"
            kw["batch_year"] = 2026
        else:
            kw["employee_id"] = f"EMP_{iid}"
        u = UserService.create_basic_user(**kw)
    return u


pytestmark = pytest.mark.django_db

# --- BR-SA-004: User Archival Eligibility ---


def test_br_009_user_archival_eligible_permitted():
    """TEST_BR_009 | BR-SA-004: Verify archival of deactivated user past minimum deactivation interval is permitted."""
    u = ensure_test_user("BR_ARCH_OK", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Retired")
    u.refresh_from_db()
    u.deactivated_at = timezone.now() - timedelta(days=60)
    u.save()

    archived = ArchivalService.archive_user(user_id=u.id, reason="Retired faculty archival")
    assert archived.status == "reversible"
    u.refresh_from_db()
    assert u.status == "archived"


def test_br_010_user_archival_active_user_prohibited():
    """TEST_BR_010 | BR-SA-004: Verify archival of an active user is prohibited."""
    u = ensure_test_user("BR_ARCH_ACT", "faculty")
    with pytest.raises(ArchivalError):
        ArchivalService.archive_user(user_id=u.id, reason="Invalid archival of active user")


def test_br_011_user_archival_unelapsed_interval_prohibited():
    """TEST_BR_011 | BR-SA-004: Verify archival of deactivated user before minimum interval has elapsed is prohibited."""
    u = ensure_test_user("BR_ARCH_EARLY", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Recently left")
    u.deactivated_at = timezone.now() - timedelta(days=2)  # Configured minimum is 30 days
    u.save()

    with pytest.raises(ArchivalError):
        ArchivalService.archive_user(
            user_id=u.id, reason="Premature archival", bypass_interval=False
        )


# --- BR-SA-005: Archived User Reversibility Window ---


def test_br_012_archived_user_restoration_within_window_permitted():
    """TEST_BR_012 | BR-SA-005: Verify restoration of archived user within reversible window with authorization is permitted."""
    u = ensure_test_user("BR_REST_OK", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archival", bypass_interval=True)

    restored = ArchivalService.restore_archived_user(
        archived_user_id=archived.id, authorization_ref="DIR-REST-2026-OK"
    )
    assert restored.status == "active"
    archived.refresh_from_db()
    assert archived.status == "restored"


def test_br_013_archived_user_restoration_missing_auth_ref_prohibited():
    """TEST_BR_013 | BR-SA-005: Verify restoration of archived user without authorization reference is prohibited."""
    u = ensure_test_user("BR_REST_NOAUTH", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archival", bypass_interval=True)

    with pytest.raises(ArchivalError):
        ArchivalService.restore_archived_user(archived_user_id=archived.id, authorization_ref="")


def test_br_014_archived_user_restoration_post_window_prohibited():
    """TEST_BR_014 | BR-SA-005: Verify restoration of archived user after reversibility deadline is prohibited (permanent)."""
    u = ensure_test_user("BR_REST_PAST", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archival", bypass_interval=True)
    archived.reversibility_deadline = timezone.now() - timedelta(days=5)
    archived.save()

    with pytest.raises(ArchivalError):
        ArchivalService.restore_archived_user(
            archived_user_id=archived.id, authorization_ref="AUTH-PAST"
        )
    # Operation rejected as expected


# --- BR-SA-017: Historical Data Archival Eligibility ---


def test_br_037_historical_archival_valid_range_permitted():
    """TEST_BR_037 | BR-SA-017: Verify archival of historical operational data satisfying retention-age criterion is permitted."""
    rec = ArchivalService.archive_historical_data(
        category="student_grades_2018",
        date_range_start=date(2018, 1, 1),
        date_range_end=date(2018, 12, 31),
        record_count=350,
        storage_size_kb=4200,
        backup_reference="BKP-HIST-2018-01",
    )
    assert rec.status == "archived"
    assert rec.record_count == 350


def test_br_038_historical_archival_inverted_date_range_prohibited():
    """TEST_BR_038 | BR-SA-017: Verify historical data archival with invalid reversed date range is prohibited."""
    with pytest.raises(ArchivalError):
        ArchivalService.archive_historical_data(
            category="finance_records",
            date_range_start=date(2025, 1, 1),
            date_range_end=date(2024, 1, 1),  # Inverted range
        )


# --- BR-SA-018: Backup Before Archival ---


def test_br_039_backup_created_before_historical_archival():
    """TEST_BR_039 | BR-SA-018: Verify a verified backup reference is created and associated prior to archival."""
    rec = ArchivalService.archive_historical_data(
        category="exam_logs_2019",
        date_range_start=date(2019, 1, 1),
        date_range_end=date(2019, 12, 31),
        record_count=200,
        storage_size_kb=1500,
    )
    assert rec.backup_reference != ""
    assert rec.summary_metadata.get("backup_created") is True


# --- BR-SA-019: Archive Retention Policy ---


def test_br_040_retention_expiry_calculation():
    """TEST_BR_040 | BR-SA-019: Verify retention expiry date is calculated and enforced based on retention policy years."""
    start = date(2015, 1, 1)
    end = date(2015, 12, 31)
    rec = ArchivalService.archive_historical_data(
        category="statutory_records_2015",
        date_range_start=start,
        date_range_end=end,
        retention_years=10,
    )
    expected_expiry = end + timedelta(days=365 * 10)
    assert rec.retention_expiry_date == expected_expiry


# --- BR-SA-020: Archived Data Access Mode ---


def test_br_041_archived_records_read_only_search_permitted(stub_iam):
    """TEST_BR_041 | BR-SA-020: Verify Super Admin can perform read-only searches and queries on archived records."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/")
    assert resp.status_code == 200


def test_br_042_direct_edit_on_archived_user_prohibited(stub_iam):
    """TEST_BR_042 | BR-SA-020: Verify direct write modification on archived user records is prohibited."""
    u = ensure_test_user("BR_EDIT_ARCH", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    ArchivalService.archive_user(user_id=u.id, reason="Archived", bypass_interval=True)

    client = get_sa_client(stub_iam)
    # Attempting to update profile of archived user
    client.put(f"/api/v1/systemadmin/users/{u.id}/", {"full_name": "Tampered Name"}, format="json")
    u.refresh_from_db()
    assert u.status == "archived"
    assert u.full_name != "Tampered Name"


# --- BR-SA-021: Permanent Purge Eligibility ---


def test_br_043_permanent_purge_eligible_past_retention_permitted():
    """TEST_BR_043 | BR-SA-021: Verify permanent purge request is permitted after retention period has expired."""
    rec = ArchivalService.archive_historical_data(
        category="expired_records",
        date_range_start=date(2010, 1, 1),
        date_range_end=date(2010, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Retention period expired",
        regulatory_authorization_ref="REG-AUTH-2026",
    )
    assert req.status in ["pending_authorization", "pending_it_head"]


def test_br_044_permanent_purge_unelapsed_retention_prohibited():
    """TEST_BR_044 | BR-SA-021: Verify permanent purge request is prohibited before retention period has elapsed."""
    rec = ArchivalService.archive_historical_data(
        category="future_retention_records",
        date_range_start=date(2022, 1, 1),
        date_range_end=date(2022, 12, 31),
    )
    rec.retention_expiry_date = date.today() + timedelta(days=365)
    rec.save()

    with pytest.raises(ArchivalError):
        ArchivalService.request_permanent_purge(
            target_type="historical_data",
            target_id=rec.id,
            reason="Premature purge",
            regulatory_authorization_ref="REG-AUTH-PREMATURE",
        )


# --- BR-SA-022: Dual Authorization for Purge ---


def test_br_045_permanent_purge_authorization_execution_permitted():
    """TEST_BR_045 | BR-SA-022: Verify permanent purge execution is permitted upon valid administrative authorization."""
    rec = ArchivalService.archive_historical_data(
        category="purge_auth_ok",
        date_range_start=date(2005, 1, 1),
        date_range_end=date(2005, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=10)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Statutory period over",
        regulatory_authorization_ref="REG-AUTH-DUAL",
    )
    authorized = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="approve",
        comments="Approved by IT Head and Super Admin",
    )
    assert authorized.status in ["approved", "completed"]
    # BR-SA-022: Permanent purge must remove target record from database
    assert not ArchivedHistoricalData.objects.filter(id=rec.id).exists()


def test_br_046_permanent_purge_unauthorized_prohibited():
    """TEST_BR_046 | BR-SA-022: Verify permanent purge execution without authorization is prohibited."""
    rec = ArchivalService.archive_historical_data(
        category="purge_auth_reject",
        date_range_start=date(2006, 1, 1),
        date_range_end=date(2006, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=10)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Testing rejection",
        regulatory_authorization_ref="REG-AUTH-REJ",
    )
    rejected = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="reject",
        comments="Rejected due to pending legal inquiry",
    )
    assert rejected.status == "rejected"
    # Target record should not be deleted
    assert ArchivedHistoricalData.objects.filter(id=rec.id).exists()
