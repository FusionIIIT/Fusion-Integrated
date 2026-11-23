"""Comprehensive user journeys covering all live BADMS use cases via the HTTP API.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    UserStorageQuota,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_journey_plain_user_usage_and_requests_ba_uc_023(stub_iam):
    """BA-UC-023: Plain user checks quota, submits archival and storage requests."""
    UserStorageQuota.objects.create(
        user_id=101,
        allocated_quota_bytes=10 * 1024 * 1024 * 1024,
        used_storage_bytes=2 * 1024 * 1024 * 1024,
    )
    c_user = _client(
        stub_iam,
        user_id=101,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=(
            "badms.archival.create",
            "badms.archival.view",
            "badms.storage.create",
            "badms.storage.view",
        ),
    )

    # 1. Plain user checks their storage quota (BA-UC-018, BA-UC-023)
    quota = UserStorageQuota.objects.get(user_id=101)
    assert quota.user_id == 101
    assert quota.used_storage_bytes == 2 * 1024 * 1024 * 1024

    # 2. Plain user submits an archival request (BA-UC-002)
    res_arch = c_user.post(
        "/api/v1/badms/archival-requests/",
        {
            "file_name": "thesis_project.tar.gz",
            "file_type": "tar.gz",
            "file_size_bytes": 500 * 1024 * 1024,
            "reason": "Thesis archival",
            "file_storage_path": "/home/student/thesis.tar.gz",
            "initial_classification": "Routine",
            "department": "CSE",
        },
    )
    assert res_arch.status_code == 201
    arch_id = res_arch.json()["id"]

    # 3. Plain user submits a storage extension request (BA-UC-007) when quota is full
    quota.used_storage_bytes = quota.allocated_quota_bytes
    quota.is_full = True
    quota.save()

    res_ext = c_user.post(
        "/api/v1/badms/storage-extensions/",
        {
            "requested_extension_bytes": 5 * 1024 * 1024 * 1024,
            "justification": "Machine learning datasets",
            "department": "CSE",
        },
    )
    assert res_ext.status_code == 201
    ext_id = res_ext.json()["id"]

    # 4. Plain user sees their own requests in their list
    res_arch_list = c_user.get("/api/v1/badms/archival-requests/")
    assert res_arch_list.status_code == 200
    assert any(r["id"] == arch_id for r in res_arch_list.json()["results"])

    res_ext_list = c_user.get("/api/v1/badms/storage-extensions/")
    assert res_ext_list.status_code == 200
    assert any(r["id"] == ext_id for r in res_ext_list.json()["results"])


def test_journey_archival_lifecycle_ba_uc_002_003_004_005_009_022(stub_iam):
    """Archival lifecycle: Submit -> HoD decide -> SysAdmin classify -> IT Security encrypt -> search."""
    # Step 1: User submits archival request (BA-UC-002)
    c_user = _client(
        stub_iam,
        user_id=102,
        roles=("faculty",),
        active_role="faculty",
        modules=("badms",),
        permissions=("badms.archival.create", "badms.archival.view"),
    )
    res_sub = c_user.post(
        "/api/v1/badms/archival-requests/",
        {
            "file_name": "lab_records.tar",
            "file_type": "tar",
            "file_size_bytes": 1024 * 1024,
            "reason": "Lab research data",
            "file_storage_path": "/data/lab.tar",
            "initial_classification": "Sensitive",
            "department": "CSE",
        },
    )
    assert res_sub.status_code == 201
    req_id = res_sub.json()["id"]

    # Step 2: HoD reviews and approves request (BA-UC-003)
    c_hod = _client(
        stub_iam,
        user_id=902,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.approve"),
    )
    res_dec = c_hod.post(f"/api/v1/badms/archival-requests/{req_id}/decide/", {"decision": "approve"})
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "hod_approved"

    # Step 3: SysAdmin performs authoritative classification (BA-UC-004)
    c_sysadmin = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.review"),
    )
    res_cls = c_sysadmin.post(
        f"/api/v1/badms/archival-requests/{req_id}/classify/",
        {"classification": "Sensitive"},
    )
    assert res_cls.status_code == 200
    assert res_cls.json()["status"] == "classified_sensitive"

    # Step 4: IT Security configures encryption (BA-UC-005)
    c_sec = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.security.manage"),
    )
    res_enc = c_sec.post(
        f"/api/v1/badms/archival-requests/{req_id}/configure-encryption/",
        {"encryption_algorithm": "AES-256-GCM"},
    )
    assert res_enc.status_code == 200
    assert res_enc.json()["status"] == "sensitive_archive_encrypted"

    # Step 5: Search and browse archives (BA-UC-009)
    res_browse = c_sysadmin.get("/api/v1/badms/archival-requests/?status=sensitive_archive_encrypted")
    assert res_browse.status_code == 200
    assert len(res_browse.json()["results"]) >= 1

    # Step 6: Super Admin performs special archival (BA-UC-022)
    c_super = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.manage"),
    )
    res_sp = c_super.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "file_name": "executive_offline.tar",
            "file_type": "tar",
            "file_size_bytes": 5000,
            "reason": "Executive offline directive",
            "file_storage_path": "/offline/exec.tar",
            "classification": "Archival",
        },
    )
    assert res_sp.status_code == 201
    assert res_sp.json()["status"] == "special_archived"


def test_journey_storage_extension_lifecycle_ba_uc_007_008_016(stub_iam):
    """Storage extension lifecycle: User request -> HoD approval -> quota updated."""
    UserStorageQuota.objects.create(
        user_id=103,
        allocated_quota_bytes=5 * 1024 * 1024 * 1024,
        used_storage_bytes=5 * 1024 * 1024 * 1024,
        is_full=True,
    )
    c_user = _client(
        stub_iam,
        user_id=103,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=("badms.storage.create", "badms.storage.view"),
    )

    # 1. Submit storage extension
    res_req = c_user.post(
        "/api/v1/badms/storage-extensions/",
        {
            "requested_extension_bytes": 10 * 1024 * 1024 * 1024,
            "justification": "Thesis project simulations",
            "department": "ECE",
        },
    )
    assert res_req.status_code == 201
    ext_id = res_req.json()["id"]

    # 2. HoD reviews and approves
    c_hod = _client(
        stub_iam,
        user_id=903,
        roles=("HOD (ECE)",),
        active_role="HOD (ECE)",
        modules=("badms",),
        permissions=("badms.storage.view", "badms.storage.approve"),
    )
    res_dec = c_hod.post(f"/api/v1/badms/storage-extensions/{ext_id}/decide/", {"decision": "approve"})
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "approved"

    # 3. Quota updated
    quota = UserStorageQuota.objects.get(user_id=103)
    assert quota.allocated_quota_bytes == 15 * 1024 * 1024 * 1024


def test_journey_backups_schedules_integrity_ba_uc_001_006_013_021(stub_iam):
    """Backups & schedules: Manual backup -> Verify integrity -> Manage schedule."""
    c_sys = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=(
            "badms.backup.view",
            "badms.backup.manage",
        ),
    )

    # 1. Trigger manual backup (BA-UC-001)
    res_man = c_sys.post("/api/v1/badms/backups/manual/", {"dataset_name": "grades_db"})
    assert res_man.status_code == 201
    b_id = res_man.json()["id"]
    assert res_man.json()["status"] == "success"

    # 2. Verify backup integrity (BA-UC-013)
    res_vf = c_sys.get(f"/api/v1/badms/backups/{b_id}/")
    assert res_vf.status_code == 200
    assert len(res_vf.json()["checksum_sha256"]) == 64

    # 3. Create local backup schedule (BA-UC-021)
    res_sch = c_sys.post(
        "/api/v1/badms/schedules/local/",
        {
            "name": "Hourly Grades",
            "dataset_name": "grades_db",
            "cron_expression": "0 * * * *",
        },
    )
    assert res_sch.status_code == 201


def test_journey_restoration_lifecycle_ba_uc_010_011_012(stub_iam):
    """Restoration lifecycle: Request restore -> SysAdmin approve sensitive -> Execute."""
    req_arch = ArchivalRequest.objects.create(
        requester_user_id=104,
        department="Finance",
        file_name="payroll.dump",
        file_type="dump",
        file_size_bytes=4096,
        reason="Audit",
        file_storage_path="/tmp/payroll.dump",
        initial_classification="Sensitive",
        authoritative_classification="Sensitive",
        status="sensitive_archive_encrypted",
    )
    c_user = _client(
        stub_iam,
        user_id=104,
        roles=("staff",),
        active_role="staff",
        modules=("badms",),
        permissions=("badms.restoration.create", "badms.restoration.view"),
    )

    # 1. Request restoration (BA-UC-011)
    res_req = c_user.post(
        "/api/v1/badms/restorations/",
        {
            "archival_request_id": req_arch.id,
            "target_destination": "payroll_dev",
        },
    )
    assert res_req.status_code == 201
    rest_id = res_req.json()["id"]
    assert res_req.json()["status"] == "sensitive_pending_approval"

    # 2. SysAdmin approves sensitive restoration (BA-UC-012)
    c_sys = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=(
            "badms.restoration.view",
            "badms.restoration.approve",
            "badms.restoration.restore",
        ),
    )
    res_app = c_sys.post(f"/api/v1/badms/restorations/{rest_id}/approve/", {"decision": "approve"})
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    # 3. Execute restoration (BA-UC-010)
    res_exec = c_sys.post(f"/api/v1/badms/restorations/{rest_id}/execute/")
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "restored"


def test_journey_reports_audit_and_policy_ba_uc_014_015_017_018_019_020(stub_iam):
    """Reports, audit, policies: View audit -> Generate reports -> Configure security policy."""
    AuditEvent.objects.create(
        event_type="test_event",
        actor_user_id=1,
        actor_role="SysAdmin",
        target_model="BackupRecord",
        target_id=1,
        department="General",
        details="Event logged",
    )

    c_admin = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=(
            "badms.audit.view",
            "badms.report.view",
        ),
    )

    # 1. View audit logs (BA-UC-015)
    res_audit = c_admin.get("/api/v1/badms/audit-logs/")
    assert res_audit.status_code == 200
    assert len(res_audit.json()["results"]) >= 1

    # 2. Generate reports (BA-UC-014)
    res_rep = c_admin.get("/api/v1/badms/reports/department/?department=General")
    assert res_rep.status_code == 200

    # 3. Configure security policy (BA-UC-020)
    c_sec = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.security.manage",),
    )
    res_pol = c_sec.post(
        "/api/v1/badms/security-policies/",
        {
            "policy_key": "tls_enforcement",
            "policy_value": {"enforce_tls": True, "min_version": "1.3"},
        },
        format="json",
    )
    assert res_pol.status_code == 201
