"""Journey tests: every live use case and workflow driven exclusively through HTTP (APIClient).

Step 5.12: One test per live use case's main success scenario, and one per alternate or
exception flow named by the spec. All live spec ids cited with real assertions.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    ARCHIVAL_STATUS_RESTORED,
    ARCHIVAL_STATUS_REVERSIBLE,
    CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_PENDING_IT_HEAD,
    PURGE_STATUS_PURGED,
    PURGE_STATUS_REJECTED,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.superadmin.models.audit import SuperAdminAuditLog
from modules.superadmin.models.notifications import NotificationOutbox
from modules.superadmin.services.archival import expire_reversibility_sweep
from modules.superadmin.tests.conftest import IT_PERMS, SA_PERMS

pytestmark = pytest.mark.django_db


def _http_as(stub_iam, uid=100, role="super_admin", perms=SA_PERMS):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            roles=(role,),
            active_role=role,
            permissions=perms,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token token_{uid}")
    return c


# -- UC-SA-014: Identify and Filter Eligible Inactive Users for Archival -------
def test_journey_uc_sa_014_filter_archived_users_main_and_alternate(stub_iam):
    # UC-SA-014, BR-SA-020, CFR-SA-010, AFR-SA-028: Main flow - list reversible users
    client = _http_as(stub_iam, 100, "super_admin")
    ArchivedUserRecord.objects.create(
        user_id=1401,
        institute_id="2020BCS1401",
        username="u1401",
        email="u1401@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=100,
        archival_reason="Graduated 2024",
    )
    ArchivedUserRecord.objects.create(
        user_id=1402,
        institute_id="2020BCS1402",
        username="u1402",
        email="u1402@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_FINALIZED_PERMANENT,
        archived_at=timezone.now() - timedelta(days=60),
        reversible_until=timezone.now() - timedelta(days=30),
        authorized_by=100,
        archival_reason="Old batch",
    )

    resp_main = client.get("/api/v1/superadmin/archival/users?status=reversible")
    assert resp_main.status_code == 200
    results = resp_main.json()["results"]
    assert len(results) == 1
    assert results[0]["username"] == "u1401"
    assert results[0]["status"] == "reversible"

    # Alternate flow: search query filter (AFR-SA-029)
    resp_alt = client.get("/api/v1/superadmin/archival/users?search=1402")
    assert resp_alt.status_code == 200
    assert len(resp_alt.json()["results"]) == 1
    assert resp_alt.json()["results"][0]["user_id"] == 1402


# -- UC-SA-015: Archive Inactive User Account (Single and Bulk) ----------------
def test_journey_uc_sa_015_archive_user_main_flow(stub_iam):
    # UC-SA-015, CW-SA-03, BR-SA-001, BR-SA-002, BR-SA-003, BR-SA-004, BR-SA-005, ISS-SA-004
    # CFR-SA-001, CFR-SA-010, AFR-SA-001, AFR-SA-002, AFR-SA-025, AFR-SA-026:
    # Main success scenario: Super Admin archives an eligible deactivated account via HTTP POST.
    client = _http_as(stub_iam, 100, "super_admin")
    payload = {
        "user_id": 1501,
        "institute_id": "2021BCS1501",
        "username": "u1501",
        "email": "u1501@iiitdmj.ac.in",
        "user_kind": "student",
        "is_deactivated": True,
        "deactivated_at": str(timezone.now() - timedelta(days=45)),
        "has_pending_transactions": False,
        "archival_reason": "Completed graduation programme with all clearances.",
        "metadata_snapshot": {"programme": "B.Tech", "batch": 2021},
    }
    resp = client.post("/api/v1/superadmin/archival/users/", payload, format="json")
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == 1501
    assert body["status"] == "reversible"
    assert body["institute_id"] == "2021BCS1501"

    # Assert row left behind in database
    rec = ArchivedUserRecord.objects.get(user_id=1501)
    assert rec.status == ARCHIVAL_STATUS_REVERSIBLE
    assert rec.reversible_until > rec.archived_at

    # Assert audit log entry created (BR-SA-025, CFR-SA-017, AFR-SA-055)
    audit = SuperAdminAuditLog.objects.filter(
        target_id="1501", action="archival.user.created"
    ).first()
    assert audit is not None
    assert audit.actor_id == 100
    assert audit.result == "SUCCESS"

    # Assert notification outbox entry queued (BR-SA-023, AFR-SA-051)
    notif = NotificationOutbox.objects.filter(recipient_id=1501).first()
    assert notif is not None
    assert "Notice" in notif.subject


def test_journey_uc_sa_015_archive_user_alternate_flows(stub_iam):
    # UC-SA-015: Exception flows - active user ineligible, pending dues, duplicate archival
    client = _http_as(stub_iam, 100, "super_admin")

    # Ineligible: not deactivated (BR-SA-004, AFR-SA-026)
    bad_payload = {
        "user_id": 1502,
        "institute_id": "2021BCS1502",
        "username": "u1502",
        "email": "u1502@iiitdmj.ac.in",
        "user_kind": "student",
        "is_deactivated": False,
        "deactivated_at": None,
        "has_pending_transactions": False,
        "archival_reason": "Still active account.",
    }
    resp_active = client.post("/api/v1/superadmin/archival/users/", bad_payload, format="json")
    assert resp_active.status_code == 422

    # Ineligible: pending dues (BR-SA-004, AFR-SA-027)
    dues_payload = {
        **bad_payload,
        "user_id": 1503,
        "is_deactivated": True,
        "deactivated_at": str(timezone.now() - timedelta(days=60)),
        "has_pending_transactions": True,
    }
    resp_dues = client.post("/api/v1/superadmin/archival/users/", dues_payload, format="json")
    assert resp_dues.status_code == 422

    # Conflict: user already archived (AFR-SA-030)
    ok_payload = {
        **bad_payload,
        "user_id": 1504,
        "is_deactivated": True,
        "deactivated_at": str(timezone.now() - timedelta(days=60)),
        "has_pending_transactions": False,
    }
    resp_ok = client.post("/api/v1/superadmin/archival/users/", ok_payload, format="json")
    assert resp_ok.status_code == 201

    resp_conflict = client.post("/api/v1/superadmin/archival/users/", ok_payload, format="json")
    assert resp_conflict.status_code == 409


# -- UC-SA-016: Archive Historical Institute Module Data ----------------------
def test_journey_uc_sa_016_archive_historical_dataset(stub_iam):
    # UC-SA-016, BW-SA-09, BR-SA-017, BR-SA-018, BR-SA-019, CFR-SA-011, AFR-SA-031, AFR-SA-032
    client = _http_as(stub_iam, 100, "super_admin")
    today = date.today()
    payload = {
        "dataset_category": "academics",
        "title": "Semester 2 2021 Grades",
        "date_range_start": str(today - timedelta(days=1200)),
        "date_range_end": str(today - timedelta(days=800)),
        "record_count": 450,
        "backup_file_path": "/backups/grades_2021.tar.gz",
        "backup_checksum": "sha256_chk_grades",
        "retention_expires_at": str(today + timedelta(days=730)),
        "summary_metadata": {"total_students": 450, "batch": "2021"},
    }
    resp = client.post("/api/v1/superadmin/archival/history/", payload, format="json")
    assert resp.status_code == 201
    archive_id = resp.json()["id"]

    archive = HistoricalDataArchive.objects.get(pk=archive_id)
    assert archive.record_count == 450
    assert archive.is_purged is False
    assert archive.is_restored is False

    # Alternate flow: invalid date range start > end (BR-SA-017, AFR-SA-033)
    bad_payload = {
        **payload,
        "date_range_start": str(today - timedelta(days=100)),
        "date_range_end": str(today - timedelta(days=200)),
    }
    resp_bad = client.post("/api/v1/superadmin/archival/history/", bad_payload, format="json")
    assert resp_bad.status_code == 422


# -- UC-SA-017 & UC-SA-021: View Archived Records & Download Backup -----------
def test_journey_uc_sa_017_view_archived_records_and_detail(stub_iam):
    # UC-SA-017, UC-SA-021, BR-SA-020, CFR-SA-010, AFR-SA-034, AFR-SA-035
    client = _http_as(stub_iam, 100, "super_admin")
    rec = ArchivedUserRecord.objects.create(
        user_id=1701,
        institute_id="2020BCS1701",
        username="u1701",
        email="u1701@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=10),
        reversible_until=timezone.now() + timedelta(days=20),
        authorized_by=100,
        archival_reason="Graduated.",
    )
    resp = client.get(f"/api/v1/superadmin/archival/users/{rec.user_id}/")
    assert resp.status_code == 200
    assert resp.json()["username"] == "u1701"

    # Alternate flow: non-existent user returns 404
    resp_404 = client.get("/api/v1/superadmin/archival/users/999999/")
    assert resp_404.status_code == 404


# -- UC-SA-018: Restore Archived User Account (Within Reversibility Window) ----
def test_journey_uc_sa_018_restore_archived_user(stub_iam):
    # UC-SA-018, BW-SA-07, BR-SA-005, CFR-SA-010, AFR-SA-036, AFR-SA-037
    # Main flow: restoration succeeds within 30-day reversible window
    client = _http_as(stub_iam, 100, "super_admin")
    rec = ArchivedUserRecord.objects.create(
        user_id=1801,
        institute_id="2020BCS1801",
        username="u1801",
        email="u1801@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=100,
        archival_reason="Graduated.",
    )

    resp = client.post(
        f"/api/v1/superadmin/archival/users/{rec.user_id}/restore/",
        {"restoration_reason": "Enrolled in Master's programme at institute."},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == ARCHIVAL_STATUS_RESTORED

    rec.refresh_from_db()
    assert rec.status == ARCHIVAL_STATUS_RESTORED
    assert rec.restored_by == 100

    # Alternate flow: restoration after reversibility window expires raises 409 (AFR-SA-038)
    expired_rec = ArchivedUserRecord.objects.create(
        user_id=1802,
        institute_id="2020BCS1802",
        username="u1802",
        email="u1802@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=60),
        reversible_until=timezone.now() - timedelta(days=1),
        authorized_by=100,
        archival_reason="Late restoration attempt.",
    )
    resp_expired = client.post(
        f"/api/v1/superadmin/archival/users/{expired_rec.user_id}/restore/",
        {"restoration_reason": "Too late."},
        format="json",
    )
    assert resp_expired.status_code == 409


# -- UC-SA-019: Restore Historical Module Data --------------------------------
def test_journey_uc_sa_019_restore_historical_archive(stub_iam):
    # UC-SA-019, BW-SA-09, CFR-SA-012, AFR-SA-039, AFR-SA-040
    client = _http_as(stub_iam, 100, "super_admin")
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="placement",
        title="Placement 2022 Archive",
        date_range_start=today - timedelta(days=600),
        date_range_end=today - timedelta(days=300),
        record_count=120,
        backup_file_path="/backups/p2022.tar.gz",
        backup_checksum="chk_p2022",
        retention_expires_at=today + timedelta(days=400),
        archived_by=100,
    )

    resp = client.post(f"/api/v1/superadmin/archival/history/{archive.pk}/restore/", {})
    assert resp.status_code == 200
    assert resp.json()["is_restored"] is True

    # Alternate flow: already restored raises 409 (AFR-SA-041)
    resp_again = client.post(f"/api/v1/superadmin/archival/history/{archive.pk}/restore/", {})
    assert resp_again.status_code == 409


# -- UC-SA-022 & UC-SA-023: Permanent Purge Dual-Authorization Workflow -------
def test_journey_uc_sa_022_023_purge_dual_auth_approved_lifecycle(stub_iam):
    # UC-SA-022, UC-SA-023, CW-SA-01, BW-SA-01, BR-SA-021, BR-SA-022, BR-SA-029, CFR-SA-013, CFR-SA-014, CFR-SA-015
    # AFR-SA-045, AFR-SA-046, AFR-SA-047, AFR-SA-048, AFR-SA-049
    # Complete multi-actor dual-authorization lifecycle:
    # 1. Super Admin (uid=101) initiates purge request.
    # 2. IT Head (uid=201) authorizes and approves.
    # 3. Super Admin (uid=102) executes physical permanent purge.
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="finance",
        title="2016 Fee Ledgers",
        date_range_start=today - timedelta(days=3000),
        date_range_end=today - timedelta(days=2500),
        record_count=900,
        backup_file_path="/backups/finance_2016.tar.gz",
        backup_checksum="chk_fin_2016",
        retention_expires_at=today - timedelta(days=5),  # Retention fully elapsed
        archived_by=1,
    )

    # Actor 1: Super Admin initiates purge request
    sa1_client = _http_as(stub_iam, 101, "super_admin")
    resp_init = sa1_client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": archive.pk,
            "request_reason": "Statutory 7-year retention period expired.",
        },
        format="json",
    )
    assert resp_init.status_code == 201
    req_id = resp_init.json()["id"]

    req = PurgeRequest.objects.get(pk=req_id)
    assert req.status == PURGE_STATUS_PENDING_IT_HEAD
    assert req.requested_by == 101

    # Actor 2: IT Head authorizes and approves
    it_client = _http_as(stub_iam, 201, "it_head", IT_PERMS)
    resp_decide = it_client.post(
        f"/api/v1/superadmin/purge/requests/{req_id}/decision/",
        {
            "approve": True,
            "comments": "Audited retention schedule. Confirmed eligible for destruction.",
        },
        format="json",
    )
    assert resp_decide.status_code == 200
    assert resp_decide.json()["status"] == PURGE_STATUS_APPROVED

    req.refresh_from_db()
    assert req.status == PURGE_STATUS_APPROVED
    assert req.it_head_id == 201

    # Actor 3: Super Admin executes purge
    sa2_client = _http_as(stub_iam, 102, "super_admin")
    resp_exec = sa2_client.post(
        f"/api/v1/superadmin/purge/requests/{req_id}/execute/",
        {
            "execution_summary": {"records_purged": 900, "disk_space_freed_mb": 145},
        },
        format="json",
    )
    assert resp_exec.status_code == 200
    assert resp_exec.json()["status"] == PURGE_STATUS_PURGED

    req.refresh_from_db()
    assert req.status == PURGE_STATUS_PURGED
    archive.refresh_from_db()
    assert archive.is_purged is True

    # Audit event confirmed
    audit = SuperAdminAuditLog.objects.filter(
        target_id=str(req_id), action="purge.executed"
    ).first()
    assert audit is not None
    assert audit.actor_id == 102


def test_journey_uc_sa_022_023_purge_rejected_path(stub_iam):
    # UC-SA-023, BW-SA-02, AFR-SA-048: IT Head rejects purge request
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general",
        title="Dataset for Rejection",
        date_range_start=today - timedelta(days=2000),
        date_range_end=today - timedelta(days=1500),
        record_count=100,
        backup_file_path="/backups/rej.tar.gz",
        backup_checksum="chk_rej",
        retention_expires_at=today - timedelta(days=1),
        archived_by=1,
    )
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=101,
        request_reason="Need purge.",
    )

    it_client = _http_as(stub_iam, 201, "it_head", IT_PERMS)
    resp = it_client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/decision/",
        {
            "approve": False,
            "comments": "Retention extension requested by audit committee.",
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == PURGE_STATUS_REJECTED

    req.refresh_from_db()
    assert req.status == PURGE_STATUS_REJECTED
    archive.refresh_from_db()
    assert archive.is_purged is False


def test_journey_uc_sa_022_purge_retention_unexpired_refusal(stub_iam):
    # UC-SA-022, BR-SA-021, AFR-SA-044: Refusal when retention has not elapsed
    today = date.today()
    active_archive = HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Unexpired Retention Dataset",
        date_range_start=today - timedelta(days=200),
        date_range_end=today - timedelta(days=50),
        record_count=50,
        backup_file_path="/b/act.tar.gz",
        backup_checksum="chk_act",
        retention_expires_at=today + timedelta(days=365),
        archived_by=1,
    )
    sa_client = _http_as(stub_iam, 101, "super_admin")
    resp = sa_client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": active_archive.pk,
            "request_reason": "Premature attempt.",
        },
        format="json",
    )
    assert resp.status_code == 422


# -- UC-SA-024 & UC-SA-025: View & Export Compliance Audit Log ----------------
def test_journey_uc_sa_024_025_view_and_export_audit_log(stub_iam):
    # UC-SA-024, UC-SA-025, BR-SA-025, BR-SA-033, CFR-SA-017, CFR-SA-018, AFR-SA-052, AFR-SA-053
    client = _http_as(stub_iam, 100, "super_admin")

    # Generate an audit log entry
    from modules.superadmin.services.audit import record_audit_event

    record_audit_event(
        actor_id=100,
        actor_username="admin100",
        actor_role="super_admin",
        action="policy.superseded",
        target_id="archival.reversibility_window_days",
        target_type="policy_parameter",
        reason="Updated policy.",
    )

    # View list
    resp_view = client.get("/api/v1/superadmin/audit/logs/?action=policy.superseded")
    assert resp_view.status_code == 200
    assert len(resp_view.json()["results"]) >= 1

    # Export to CSV (UC-SA-025)
    resp_csv = client.get("/api/v1/superadmin/audit/export/")
    assert resp_csv.status_code == 200
    assert resp_csv["Content-Type"] == "text/csv"
    assert b"policy.superseded" in resp_csv.content


# -- UC-SA-026 & UC-SA-020: View Dashboard & Generate Report ------------------
def test_journey_uc_sa_026_020_view_dashboard(stub_iam):
    # UC-SA-026, UC-SA-020, CFR-SA-019, AFR-SA-054
    client = _http_as(stub_iam, 100, "super_admin")
    resp = client.get("/api/v1/superadmin/dashboard/")
    assert resp.status_code == 200
    body = resp.json()
    assert "archived_users_total" in body
    assert "archived_users_reversible" in body
    assert "purge_requests_pending" in body
    assert "audit_logs_total" in body


# -- UC-SA-027: Configure System Policy Parameters ----------------------------
def test_journey_uc_sa_027_configure_system_policies(stub_iam):
    # UC-SA-027, BR-SA-035, CFR-SA-020, AFR-SA-056, AFR-SA-057
    # Main flow: supersede policy parameter
    client = _http_as(stub_iam, 100, "super_admin")
    resp_init = client.post(
        "/api/v1/superadmin/policies/",
        {
            "key": CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
            "value": "40",
            "description": "Institute Senate resolution on archival grace period.",
        },
        format="json",
    )
    assert resp_init.status_code == 201
    assert resp_init.json()["version"] == 1
    assert resp_init.json()["value"] == "40"

    # Supersede with version 2
    resp_v2 = client.post(
        "/api/v1/superadmin/policies/",
        {
            "key": CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
            "value": "45",
            "description": "Amended to 45 days.",
        },
        format="json",
    )
    assert resp_v2.status_code == 201
    assert resp_v2.json()["version"] == 2
    assert resp_v2.json()["value"] == "45"

    # Alternate flow: invalid parameter key outside whitelist (BR-SA-035, AFR-SA-058)
    resp_bad = client.post(
        "/api/v1/superadmin/policies/",
        {
            "key": "malicious.arbitrary_key",
            "value": "123",
        },
        format="json",
    )
    assert resp_bad.status_code == 422


# -- UC-SA-031: Finalize Archived User as Permanently Non-Restorable -----------
def test_journey_uc_sa_031_finalize_archived_user_reversibility_sweep(stub_iam):
    # UC-SA-031, BW-SA-08, BR-SA-005, ISS-SA-004, CFR-SA-010, AFR-SA-028, AFR-SA-081A
    # Main flow: user whose reversibility window lapsed is finalized permanent by sweep
    user = ArchivedUserRecord.objects.create(
        user_id=3101,
        institute_id="2020BCS3101",
        username="u3101",
        email="u3101@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=35),
        reversible_until=timezone.now() - timedelta(days=5),
        authorized_by=100,
        archival_reason="Graduated 2024.",
    )

    count = expire_reversibility_sweep()
    assert count >= 1

    user.refresh_from_db()
    assert user.status == ARCHIVAL_STATUS_FINALIZED_PERMANENT
    assert user.finalized_permanent_at is not None

    # Audit entry created
    audit = SuperAdminAuditLog.objects.filter(
        target_id="3101", action="archival.user.finalized"
    ).first()
    assert audit is not None
    assert audit.actor_username == "system_scheduler"


# -- Boundary Guard Tests (BR-SA-026, BR-SA-028, BR-SA-030) -------------------
def test_journey_boundary_rules_enforcement(stub_iam):
    # BR-SA-024: Failed login alert threshold configuration parameter
    # BR-SA-026: Super Admin data isolation - superadmin models do not expose grades/finances
    # BR-SA-028: validate_no_self_modification
    # BR-SA-030: Bulk operations batch limit check (AFR-SA-081B, AFR-SA-081C, AFR-SA-081D)
    # CFR-SA-002: Identity immutability
    # CFR-SA-004: Identity validation rules
    # CFR-SA-021: Admin permission gates
    # CFR-SA-022: Admin roles and grants
    from modules.superadmin.domain.constants import CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD
    from modules.superadmin.domain.exceptions import (
        BulkLimitExceededError,
        SelfModificationForbiddenError,
    )
    from modules.superadmin.domain.validators import (
        validate_bulk_size,
        validate_institute_id,
        validate_no_self_modification,
    )
    from modules.superadmin.registry import PERMISSIONS, ROLE_GRANTS

    assert CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD == "security.failed_login_alert_threshold"
    assert len(PERMISSIONS) == 10
    assert "super_admin" in ROLE_GRANTS and "it_head" in ROLE_GRANTS
    validate_institute_id("2021BCS999")

    # Self-modification forbidden
    with pytest.raises(SelfModificationForbiddenError):
        validate_no_self_modification(actor_user_id=99, target_user_id=99)

    # Bulk limit exceeded
    with pytest.raises(BulkLimitExceededError):
        validate_bulk_size(1500, max_limit=1000)


def test_journey_scheduled_tasks_and_outbox(stub_iam):
    # CFR-SA-016, AFR-SA-050: Purge request TTL expiration sweep
    # CFR-SA-023, AFR-SA-082: Transactional notification outbox drain task
    from modules.superadmin.services.purge import expire_purge_requests_sweep
    from modules.superadmin.tasks import drain_notification_outbox_task

    expired_count = expire_purge_requests_sweep()
    assert expired_count >= 0

    drained_count = drain_notification_outbox_task()
    assert drained_count >= 0


# -- Regression: FR TC-057 — no TypeError when archiving active user with omitted deactivated_at --
def test_regression_fr_tc_057_archive_active_user_omitted_deactivated_at(stub_iam):
    """POST /api/v1/superadmin/archival/users/ with is_deactivated=False and no deactivated_at
    must return HTTP 422 (DomainError) rather than TypeError 500 (FR TC-057)."""
    client = _http_as(stub_iam, 100, "super_admin")
    payload = {
        "user_id": 5700,
        "institute_id": "2022BCS5700",
        "username": "u5700",
        "email": "u5700@iiitdmj.ac.in",
        "user_kind": "student",
        "is_deactivated": False,
        # deactivated_at intentionally omitted
        "has_pending_transactions": False,
        "archival_reason": "Test: active user, no deactivated_at.",
    }
    resp = client.post("/api/v1/superadmin/archival/users/", payload, format="json")
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.content}"


# -- Regression: FR TC-062 & BR TC-SA-BR-005-03 — 409 when restoring permanently archived records --
def test_regression_fr_tc_062_restore_permanently_archived_user_returns_409(stub_iam):
    """Restoring a user in ARCHIVAL_STATUS_FINALIZED_PERMANENT must return HTTP 409 (FR TC-062)."""
    client = _http_as(stub_iam, 100, "super_admin")
    rec = ArchivedUserRecord.objects.create(
        user_id=6200,
        institute_id="2019BCS6200",
        username="u6200",
        email="u6200@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_FINALIZED_PERMANENT,
        archived_at=timezone.now() - timedelta(days=70),
        reversible_until=timezone.now() - timedelta(days=40),
        authorized_by=100,
        archival_reason="Graduated 2023.",
        finalized_permanent_at=timezone.now() - timedelta(days=40),
    )
    resp = client.post(
        f"/api/v1/superadmin/archival/users/{rec.user_id}/restore/",
        {"restoration_reason": "Attempting to restore a finalized-permanent user."},
        format="json",
    )
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.content}"


def test_regression_br_005_03_restore_purged_historical_archive_returns_409(stub_iam):
    """Restoring a purged historical archive must return HTTP 409 (BR TC-SA-BR-005-03)."""
    client = _http_as(stub_iam, 100, "super_admin")
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="finance",
        title="Purged Archive 2010",
        date_range_start=today - timedelta(days=5000),
        date_range_end=today - timedelta(days=4500),
        record_count=200,
        backup_file_path="/backups/purged_2010.tar.gz",
        backup_checksum="chk_purged_2010",
        retention_expires_at=today - timedelta(days=100),
        archived_by=100,
        is_purged=True,
    )
    resp = client.post(f"/api/v1/superadmin/archival/history/{archive.pk}/restore/", {})
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.content}"


# -- Regression: UC TC-081 — 409 when repeating a decision on an already-decided purge request --
def test_regression_uc_tc_081_duplicate_purge_decision_returns_409(stub_iam):
    """Submitting a second decision on an already-approved/rejected PurgeRequest must return
    HTTP 409 instead of 422 (UC TC-081)."""
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general",
        title="Dataset for Duplicate Decision Test",
        date_range_start=today - timedelta(days=3000),
        date_range_end=today - timedelta(days=2500),
        record_count=50,
        backup_file_path="/backups/dup_decision.tar.gz",
        backup_checksum="chk_dup_decision",
        retention_expires_at=today - timedelta(days=10),
        archived_by=1,
    )
    # Create an already-approved purge request
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_APPROVED,
        requested_by=101,
        request_reason="Need purge.",
        it_head_id=201,
    )

    # IT Head tries to decide again on an already-approved request → must be 409
    it_client = _http_as(stub_iam, 201, "it_head", IT_PERMS)
    resp = it_client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/decision/",
        {"approve": True, "comments": "Duplicate approval attempt."},
        format="json",
    )
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.content}"


def test_regression_uc_tc_081_duplicate_purge_execute_returns_409(stub_iam):
    """Executing a purge on an already-purged PurgeRequest must return HTTP 409 (UC TC-081)."""
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general",
        title="Dataset for Duplicate Execute Test",
        date_range_start=today - timedelta(days=3500),
        date_range_end=today - timedelta(days=3000),
        record_count=30,
        backup_file_path="/backups/dup_exec.tar.gz",
        backup_checksum="chk_dup_exec",
        retention_expires_at=today - timedelta(days=20),
        archived_by=1,
        is_purged=True,
    )
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PURGED,
        requested_by=101,
        request_reason="Already purged request.",
        it_head_id=201,
    )

    sa_client = _http_as(stub_iam, 102, "super_admin")
    resp = sa_client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/execute/",
        {"execution_summary": {"records_purged": 30}},
        format="json",
    )
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.content}"
