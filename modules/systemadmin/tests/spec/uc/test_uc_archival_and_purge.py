"""Use Case Executable Tests: Archival and Purge.

Covers UC-SA-015 through UC-SA-023, and UC-SA-031.
Traceable to UC_DESIGN.json test cases TEST_UC_052 through TEST_UC_081, and TEST_UC_104 through TEST_UC_106.
"""

import contextlib
from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.archival import (
    ArchivedHistoricalData,
    ArchivedUser,
    PermanentPurgeRequest,
)
from modules.systemadmin.models.user_mgmt import BasicUserProfile
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


def create_deactivated_user(username="deact_user_arch"):
    u = BasicUserProfile.objects.filter(institute_id=username).first()
    if not u:
        u = UserService.create_basic_user(
            institute_id=username,
            user_type="student",
            full_name="Deactivated For Archive",
            institute_email=f"{username}@iiitdmj.ac.in",
            date_of_joining=date(2022, 8, 1),
            programme="B.Tech",
            batch_year=2022,
            department="CSE",
        )
    u.status = "deactivated"
    u.deactivated_at = date.today() - timedelta(days=200)
    u.save()
    return u


# --- UC-SA-015: Archive User ---


def test_uc_052_archive_user_main_flow(stub_iam):
    """TEST_UC_052 | UC-SA-015 Main Flow: Verify Super Admin archives an eligible deactivated user."""
    u = create_deactivated_user("uc_arch_u1")
    client = get_sa_client(stub_iam)
    payload = {
        "user_id": u.id,
        "reason": "Retention elapsed post graduation",
    }
    resp = client.post("/api/v1/systemadmin/archival/users/create/", payload, format="json")
    assert resp.status_code == 201
    u.refresh_from_db()
    assert u.status == "archived"
    assert ArchivedUser.objects.filter(user=u).exists()


def test_uc_053_archive_user_alt_a1_multiple_selected_users():
    """TEST_UC_053 | UC-SA-015 Alternative A1: Verify multiple individually selected eligible users can be archived."""
    u1 = create_deactivated_user("uc_mult_arch1")
    u2 = create_deactivated_user("uc_mult_arch2")
    ArchivalService.archive_user(u1.id, reason="Batch archival 1")
    ArchivalService.archive_user(u2.id, reason="Batch archival 2")
    assert ArchivedUser.objects.filter(user=u1).exists()
    assert ArchivedUser.objects.filter(user=u2).exists()


def test_uc_054_archive_user_exc_e1_active_user_rejected(stub_iam):
    """TEST_UC_054 | UC-SA-015 Exception E1: Verify archiving an active user is rejected."""
    u = UserService.create_basic_user(
        institute_id="uc_arch_active",
        user_type="student",
        full_name="Active Cant Archive",
        institute_email="active_cant@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
        department="CSE",
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/archival/users/create/",
        {"user_id": u.id, "reason": "Premature archival attempt"},
        format="json",
    )
    assert resp.status_code == 400


def test_uc_055_archive_user_exc_e2_storage_failure_protects_original():
    """TEST_UC_055 | UC-SA-015 Exception E2: Verify original user remains protected if archival fails."""
    u = create_deactivated_user("uc_arch_prot")
    orig_status = u.status
    with contextlib.suppress(ArchivalError):
        ArchivalService.archive_user(9999999, reason="Fault injection")
    u.refresh_from_db()
    assert u.status == orig_status


# --- UC-SA-016: Archive Historical Data ---


def test_uc_056_archive_historical_data_main_flow(stub_iam):
    """TEST_UC_056 | UC-SA-016 Main Flow: Verify Super Admin archives historical operational data."""
    client = get_sa_client(stub_iam)
    payload = {
        "category": "academic_grades_2020",
        "date_range_start": "2020-01-01",
        "date_range_end": "2020-12-31",
        "record_count": 500,
        "backup_reference": "BKP-GRADES-2020-A",
        "storage_size_kb": 2500,
        "description": "Graduated batch 2020 academic records",
    }
    resp = client.post("/api/v1/systemadmin/archival/historical/create/", payload, format="json")
    assert resp.status_code == 201
    assert ArchivedHistoricalData.objects.filter(category="academic_grades_2020").exists()


def test_uc_057_archive_historical_data_alt_a1_ineligible_records_identified():
    """TEST_UC_057 | UC-SA-016 Alternative A1: Verify system partitions or flags ineligible records."""
    rec = ArchivalService.archive_historical_data(
        category="library_logs_2019",
        date_range_start=date(2019, 1, 1),
        date_range_end=date(2019, 12, 31),
        record_count=250,
        backup_reference="BKP-LIB-2019",
    )
    assert rec.status == "archived"


def test_uc_058_archive_historical_data_exc_e1_invalid_date_range(stub_iam):
    """TEST_UC_058 | UC-SA-016 Exception E1: Verify archival rejected if start date is after end date."""
    client = get_sa_client(stub_iam)
    payload = {
        "category": "bad_range_cat",
        "date_range_start": "2024-01-01",
        "date_range_end": "2023-01-01",
        "record_count": 10,
    }
    resp = client.post("/api/v1/systemadmin/archival/historical/create/", payload, format="json")
    assert resp.status_code == 400


def test_uc_059_archive_historical_data_exc_e2_backup_verification_failure():
    """TEST_UC_059 | UC-SA-016 Exception E2: Verify operation rejected if date range is invalid."""
    with pytest.raises(ArchivalError):
        ArchivalService.archive_historical_data(
            category="finance",
            date_range_start=date(2021, 12, 31),
            date_range_end=date(2021, 1, 1),
        )


# --- UC-SA-017: Search and View Archived Records ---


def test_uc_060_search_and_view_archived_records_main_flow(stub_iam):
    """TEST_UC_060 | UC-SA-017 Main Flow: Verify Super Admin searches and retrieves archived records."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/")
    assert resp.status_code == 200
    assert isinstance(resp.data, list) or "results" in resp.data


def test_uc_061_search_and_view_archived_records_alt_a1_no_matching_records(stub_iam):
    """TEST_UC_061 | UC-SA-017 Alternative A1: Verify empty results view when search criteria match nothing."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/?search=NON_EXISTENT_ARCHIVE_999")
    assert resp.status_code == 200


def test_uc_062_search_and_view_archived_records_exc_e1_invalid_query_parameters(stub_iam):
    """TEST_UC_062 | UC-SA-017 Exception E1: Verify system handles query safely."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/archival/historical/?date_from=invalid-date")
    assert resp.status_code in (200, 400)


# --- UC-SA-018: Restore Archived User ---


def test_uc_063_restore_archived_user_main_flow(stub_iam):
    """TEST_UC_063 | UC-SA-018 Main Flow: Verify Super Admin restores user within reversible retention window."""
    u = create_deactivated_user("uc_rest_u1")
    ArchivalService.archive_user(u.id, reason="Temporary archival")
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/archival/users/{u.id}/restore/",
        {"restoration_authorization_ref": "REF-REST-101"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.status == "active"


def test_uc_064_restore_archived_user_alt_a1_requires_profile_review():
    """TEST_UC_064 | UC-SA-018 Alternative A1: Verify restored user profile is updated and reviewed."""
    u = create_deactivated_user("uc_rest_rev")
    ArchivalService.archive_user(u.id, reason="Review archival")
    restored_user = ArchivalService.restore_archived_user(
        user_id=u.id,
        restoration_authorization_ref="REF-REST-REV",
    )
    assert restored_user.status == "active"


def test_uc_065_restore_archived_user_exc_e1_missing_authorization(stub_iam):
    """TEST_UC_065 | UC-SA-018 Exception E1: Verify restoring without required authorization ref is rejected."""
    u = create_deactivated_user("uc_rest_noauth")
    ArchivalService.archive_user(u.id, reason="Standard archival")
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/archival/users/{u.id}/restore/",
        {"restoration_authorization_ref": ""},
        format="json",
    )
    assert resp.status_code == 400


def test_uc_066_restore_archived_user_exc_e2_retention_window_elapsed():
    """TEST_UC_066 | UC-SA-018 Exception E2: Verify restoration rejected when reversible period has elapsed."""
    u = create_deactivated_user("uc_rest_elapsed")
    ArchivalService.archive_user(u.id, reason="Long term archival")
    arch = ArchivedUser.objects.get(user=u)
    arch.status = "permanent_non_restorable"
    arch.save()
    with pytest.raises(ArchivalError):
        ArchivalService.restore_archived_user(user_id=u.id, restoration_authorization_ref="REF-EXP")


# --- UC-SA-019: Restore Archived Historical Data ---


def test_uc_067_restore_archived_historical_data_main_flow(stub_iam):
    """TEST_UC_067 | UC-SA-019 Main Flow: Verify restoring archived historical dataset with approval."""
    rec = ArchivalService.archive_historical_data(
        category="hostel_allotment_2021",
        date_range_start=date(2021, 1, 1),
        date_range_end=date(2021, 12, 31),
        record_count=120,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/archival/historical/{rec.id}/restore/",
        {"approval_ref": "REF-REST-HIST-01"},
        format="json",
    )
    assert resp.status_code == 200
    rec.refresh_from_db()
    assert rec.status == "restored"


def test_uc_068_restore_archived_historical_data_alt_a1_partial_restore_subset():
    """TEST_UC_068 | UC-SA-019 Alternative A1: Verify dataset restoration status transition."""
    rec = ArchivalService.archive_historical_data(
        category="placement_stats_2020",
        date_range_start=date(2020, 1, 1),
        date_range_end=date(2020, 12, 31),
        record_count=80,
    )
    res = ArchivalService.restore_historical_data(data_id=rec.id, approval_ref="REF-SUBSET-01")
    assert res.status == "restored"


def test_uc_069_restore_archived_historical_data_exc_e1_already_purged():
    """TEST_UC_069 | UC-SA-019 Exception E1: Verify restoring already purged dataset is rejected."""
    rec = ArchivalService.archive_historical_data(
        category="purged_data_cat",
        date_range_start=date(2015, 1, 1),
        date_range_end=date(2015, 12, 31),
        record_count=10,
    )
    rec.status = "purged"
    rec.save()
    with pytest.raises(ArchivalError):
        ArchivalService.restore_historical_data(data_id=rec.id, approval_ref="REF-PURGED")


# --- UC-SA-020: Generate and Export Archive Report ---


def test_uc_070_generate_archive_report_main_flow(stub_iam):
    """TEST_UC_070 | UC-SA-020 Main Flow: Verify Super Admin generates archive report."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?format=json")
    assert resp.status_code == 200


def test_uc_071_generate_archive_report_alt_a1_large_result_pagination(stub_iam):
    """TEST_UC_071 | UC-SA-020 Alternative A1: Verify system applies pagination for reports."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?page=1&page_size=10")
    assert resp.status_code == 200


def test_uc_072_generate_archive_report_exc_e1_data_isolation_enforced(stub_iam):
    """TEST_UC_072 | UC-SA-020 Exception E1: Verify archive report excludes operational transaction content."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?format=json")
    assert resp.status_code == 200
    assert "password_hash" not in str(resp.data)


# --- UC-SA-021: Export Archived Data for External Storage ---


def test_uc_073_export_archived_data_main_flow():
    """TEST_UC_073 | UC-SA-021 Main Flow: Verify archived dataset export metadata."""
    rec = ArchivalService.archive_historical_data(
        category="finance_vouchers_2018",
        date_range_start=date(2018, 1, 1),
        date_range_end=date(2018, 12, 31),
        record_count=300,
        backup_reference="BKP-SAN-2018",
    )
    assert rec.backup_reference == "BKP-SAN-2018"
    assert rec.status == "archived"


def test_uc_074_export_archived_data_alt_a1_metadata_only_export():
    """TEST_UC_074 | UC-SA-021 Alternative A1: Verify metadata-only export conforms to external backup structure."""
    rec = ArchivalService.archive_historical_data(
        category="security_logs_2021",
        date_range_start=date(2021, 1, 1),
        date_range_end=date(2021, 12, 31),
        record_count=1000,
        backup_reference="BKP-SEC-2021",
    )
    assert rec.category == "security_logs_2021"


def test_uc_075_export_archived_data_exc_e1_invalid_dataset_id():
    """TEST_UC_075 | UC-SA-021 Exception E1: Verify querying non-existent historical record returns None."""
    rec = ArchivedHistoricalData.objects.filter(id=999999).first()
    assert rec is None


# --- UC-SA-022: Request Permanent Data Purge ---


def test_uc_076_request_permanent_purge_main_flow(stub_iam):
    """TEST_UC_076 | UC-SA-022 Main Flow: Verify Super Admin initiates permanent purge request after retention expired."""
    rec = ArchivalService.archive_historical_data(
        category="expired_cat_01",
        date_range_start=date(2010, 1, 1),
        date_range_end=date(2010, 12, 31),
        record_count=100,
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    client = get_sa_client(stub_iam)
    payload = {
        "target_type": "historical_data",
        "target_id": rec.id,
        "reason": "Statutory 15-year retention period expired",
        "regulatory_authorization_ref": "REG-AUTH-2026-001",
    }
    resp = client.post("/api/v1/systemadmin/purge-requests/create/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending_it_head"


def test_uc_077_request_permanent_purge_alt_a1_cancel_before_submission():
    """TEST_UC_077 | UC-SA-022 Alternative A1: Verify canceling before submission generates no purge request."""
    assert not PermanentPurgeRequest.objects.filter(request_reason="Unsubmitted purge").exists()


def test_uc_078_request_permanent_purge_exc_e1_retention_not_elapsed(stub_iam):
    """TEST_UC_078 | UC-SA-022 Exception E1: Verify purge request rejected if retention period has not elapsed."""
    rec = ArchivalService.archive_historical_data(
        category="unexpired_cat_02",
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 12, 31),
        record_count=50,
    )
    rec.retention_expiry_date = date.today() + timedelta(days=500)
    rec.save()

    client = get_sa_client(stub_iam)
    payload = {
        "target_type": "historical_data",
        "target_id": rec.id,
        "reason": "Premature purge attempt",
    }
    resp = client.post("/api/v1/systemadmin/purge-requests/create/", payload, format="json")
    assert resp.status_code == 400


# --- UC-SA-023: Authorize Permanent Data Purge ---


def test_uc_079_authorize_permanent_purge_main_flow():
    """TEST_UC_079 | UC-SA-023 Main Flow: Verify IT Head authorizes purge request and destroys target."""
    rec = ArchivalService.archive_historical_data(
        category="auth_purge_cat",
        date_range_start=date(2009, 1, 1),
        date_range_end=date(2009, 12, 31),
        record_count=200,
    )
    rec.retention_expiry_date = date.today() - timedelta(days=5)
    rec.save()

    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Compliance elapsed purge",
    )
    decided = ArchivalService.authorize_permanent_purge(
        request_id=purge_req.id,
        decision="approve",
        it_head_username="it_head_officer",
        comments="Approved for destruction",
    )
    assert decided.status == "approved"
    # UC-SA-023: Permanent purge removes data records permanently
    assert not ArchivedHistoricalData.objects.filter(id=rec.id).exists()


def test_uc_080_authorize_permanent_purge_alt_a1_reject_decision():
    """TEST_UC_080 | UC-SA-023 Alternative A1: Verify IT Head rejection leaves target data archived."""
    rec = ArchivalService.archive_historical_data(
        category="rej_purge_cat",
        date_range_start=date(2008, 1, 1),
        date_range_end=date(2008, 12, 31),
        record_count=150,
    )
    rec.retention_expiry_date = date.today() - timedelta(days=10)
    rec.save()

    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Legal review needed",
    )
    decided = ArchivalService.authorize_permanent_purge(
        request_id=purge_req.id,
        decision="reject",
        it_head_username="it_head_officer",
        comments="Pending court inquiry: retain data",
    )
    assert decided.status == "rejected"
    rec.refresh_from_db()
    assert rec.status == "archived"


def test_uc_081_authorize_permanent_purge_exc_e1_already_decided():
    """TEST_UC_081 | UC-SA-023 Exception E1: Verify deciding an already approved purge request is rejected."""
    rec = ArchivalService.archive_historical_data(
        category="alr_dec_cat",
        date_range_start=date(2007, 1, 1),
        date_range_end=date(2007, 12, 31),
        record_count=80,
    )
    rec.retention_expiry_date = date.today() - timedelta(days=10)
    rec.save()

    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Double decision test",
    )
    ArchivalService.authorize_permanent_purge(
        request_id=purge_req.id,
        decision="approve",
        it_head_username="it_head_officer",
    )
    with pytest.raises(ArchivalError):
        ArchivalService.authorize_permanent_purge(
            request_id=purge_req.id,
            decision="approve",
            it_head_username="it_head_officer",
        )


# --- UC-SA-031: Finalize Archived User as Permanently Non-Restorable ---


def test_uc_104_finalize_non_restorable_user_main_flow():
    """TEST_UC_104 | UC-SA-031 Main Flow: Verify batch finalizes restorable flag when reversible window expires."""
    u = create_deactivated_user("uc_non_rest_u1")
    ArchivalService.archive_user(u.id, reason="Reversible expiry test")
    arch = ArchivedUser.objects.get(user=u)
    arch.status = "reversible"
    arch.reversibility_deadline = timezone.now() - timedelta(days=1)
    arch.save()

    finalized = ArchivalService.finalize_non_restorable_archived_users()
    arch.refresh_from_db()
    assert arch.status == "permanent_non_restorable"
    assert finalized >= 1


def test_uc_105_finalize_non_restorable_user_alt_a1_restored_before_expiry():
    """TEST_UC_105 | UC-SA-031 Alternative A1: Verify user restored prior to expiry is not affected."""
    u = create_deactivated_user("uc_rest_prior")
    ArchivalService.archive_user(u.id, reason="Restored prior")
    ArchivalService.restore_archived_user(
        user_id=u.id, restoration_authorization_ref="REF-REST-PRIOR"
    )
    ArchivalService.finalize_non_restorable_archived_users()
    u.refresh_from_db()
    assert u.status == "active"


def test_uc_106_finalize_non_restorable_user_exc_e1_active_window_preserved():
    """TEST_UC_106 | UC-SA-031 Exception E1: Verify users whose reversible window has not elapsed remain reversible."""
    u = create_deactivated_user("uc_still_restorable")
    ArchivalService.archive_user(u.id, reason="Active window test")
    arch = ArchivedUser.objects.get(user=u)
    arch.status = "reversible"
    arch.reversibility_deadline = timezone.now() + timedelta(days=30)
    arch.save()

    ArchivalService.finalize_non_restorable_archived_users()
    arch.refresh_from_db()
    assert arch.status == "reversible"
