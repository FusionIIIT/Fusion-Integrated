"""End-to-end API tests for all BADMS endpoints.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    RestorationRequest,
    StorageExtensionRequest,
    UserStorageQuota,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_backup_list_and_manual_trigger_api(stub_iam):
    BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="central_db",
        status="success",
        file_path="/tmp/c.dump",
        file_size_bytes=1000,
        checksum_sha256="abc12345",
    )

    c = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.view", "badms.backup.manage"),
    )
    res = c.get("/api/v1/badms/backups/")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1

    res_post = c.post("/api/v1/badms/backups/manual/", {"dataset_name": "student_records"})
    assert res_post.status_code == 201
    assert res_post.json()["dataset_name"] == "student_records"
    assert res_post.json()["status"] == "success"


def test_schedules_crud_api(stub_iam):
    c = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.backup.view", "badms.backup.manage", "badms.backup_policy.manage"),
    )

    # Create global schedule
    res_create = c.post(
        "/api/v1/badms/schedules/global/",
        {
            "name": "Nightly Core DB",
            "dataset_name": "fusion_main",
            "cron_expression": "0 1 * * *",
            "data_classification_filter": "all",
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["name"] == "Nightly Core DB"
    assert res_create.json()["scope_type"] == "global"

    # List schedules
    res_list = c.get("/api/v1/badms/schedules/")
    assert res_list.status_code == 200
    assert len(res_list.json()["results"]) >= 1


def test_schedules_conflict_returns_409_api(stub_iam):
    """Regression test for AFR-BA-014: Conflicting schedules return 409 Conflict with actionable message."""
    c = _client(
        stub_iam,
        user_id=1,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.manage",),
    )

    # 1. First schedule creation succeeds
    res1 = c.post(
        "/api/v1/badms/schedules/local/",
        {
            "name": "Local DB Schedule",
            "dataset_name": "unique_dataset_afr_014",
            "cron_expression": "0 2 * * *",
        },
    )
    assert res1.status_code == 201

    # 2. Conflicting schedule creation returns HTTP 409 Conflict
    res2 = c.post(
        "/api/v1/badms/schedules/local/",
        {
            "name": "Conflicting Local DB Schedule",
            "dataset_name": "unique_dataset_afr_014",
            "cron_expression": "0 3 * * *",
        },
    )
    assert res2.status_code == 409
    error_data = res2.json()["error"]
    assert error_data["code"] == "conflict"
    assert "unique_dataset_afr_014" in error_data["message"]
    assert "Update the existing schedule or deactivate it" in error_data["message"]

    # 3. Exactly one active schedule persisted in DB
    from modules.badms.models import BackupSchedule

    assert (
        BackupSchedule.objects.filter(
            dataset_name="unique_dataset_afr_014", is_active=True
        ).count()
        == 1
    )


def test_archival_requests_lifecycle_api(stub_iam):
    # 1. Student submits request
    c_student = _client(
        stub_iam,
        user_id=1001,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.create"),
    )
    res_sub = c_student.post(
        "/api/v1/badms/archival-requests/",
        {
            "department": "CSE",
            "file_name": "btech_project.zip",
            "file_type": "zip",
            "file_size_bytes": 1048576,
            "reason": "Final year capstone submission",
            "file_storage_path": "/uploads/1001/btech_project.zip",
            "initial_classification": "Sensitive",
        },
    )
    assert res_sub.status_code == 201
    req_id = res_sub.json()["id"]

    # 2. HOD CSE approves
    c_hod = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.approve"),
    )
    res_hod = c_hod.post(
        f"/api/v1/badms/archival-requests/{req_id}/decide/",
        {"decision": "approve", "remarks": "Approved by HOD"},
    )
    assert res_hod.status_code == 200
    assert res_hod.json()["status"] == "hod_approved"

    # 3. SysAdmin classifies
    c_sys = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.review"),
    )
    res_class = c_sys.post(
        f"/api/v1/badms/archival-requests/{req_id}/classify/",
        {
            "classification": "Sensitive",
        },
    )
    assert res_class.status_code == 200
    assert res_class.json()["status"] == "classified_sensitive"

    # 4. IT Security encrypts
    c_itsec = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.security.manage"),
    )
    res_enc = c_itsec.post(
        f"/api/v1/badms/archival-requests/{req_id}/configure-encryption/",
        {"encryption_algorithm": "AES-256-GCM"},
    )
    assert res_enc.status_code == 200
    assert res_enc.json()["status"] == "sensitive_archive_encrypted"


def test_storage_extension_api(stub_iam):
    UserStorageQuota.objects.create(
        user_id=1001,
        allocated_quota_bytes=10737418240,
        used_storage_bytes=10737418240,
        is_full=True,
    )

    c_student = _client(
        stub_iam,
        user_id=1001,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=("badms.storage.view", "badms.storage.create"),
    )
    res_sub = c_student.post(
        "/api/v1/badms/storage-extensions/",
        {
            "department": "CSE",
            "requested_extension_bytes": 5368709120,
            "justification": "Graduate thesis dataset requirements",
        },
    )
    assert res_sub.status_code == 201
    ext_id = res_sub.json()["id"]

    c_hod = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.storage.view", "badms.storage.approve"),
    )
    res_rev = c_hod.post(
        f"/api/v1/badms/storage-extensions/{ext_id}/decide/",
        {"decision": "approve", "remarks": "Approved 5 GB extension"},
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "approved"


def test_restoration_api_flow(stub_iam):
    arch = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="lab_code.tar",
        file_type="tar",
        file_size_bytes=1000,
        file_storage_path="/p/lab.tar",
        status="classified_non_sensitive",
        authoritative_classification="Routine",
    )

    c_user = _client(
        stub_iam,
        user_id=1001,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=("badms.restoration.view", "badms.restoration.create"),
    )
    res_sub = c_user.post(
        "/api/v1/badms/restorations/",
        {
            "archival_request_id": arch.id,
            "target_destination": "/tmp/restored_lab",
        },
    )
    assert res_sub.status_code == 201
    rest_id = res_sub.json()["id"]
    assert res_sub.json()["status"] == "requested_standard"

    # SysAdmin executes restore
    c_sys = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.restoration.view", "badms.restoration.restore"),
    )
    res_exec = c_sys.post(f"/api/v1/badms/restorations/{rest_id}/execute/", {})
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "restored"


def test_audit_logs_and_security_policies_api(stub_iam):
    AuditEvent.objects.create(
        event_type="security.test",
        actor_user_id=1,
        actor_role="Super Admin",
        target_model="SecurityPolicy",
        target_id=1,
        department="Central",
        details={"info": "Audit logged"},
    )

    c_sec = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.audit.view", "badms.security.manage", "badms.report.view"),
    )
    res_audit = c_sec.get("/api/v1/badms/audit-logs/")
    assert res_audit.status_code == 200
    assert len(res_audit.json()["results"]) >= 1

    res_pol = c_sec.post(
        "/api/v1/badms/security-policies/",
        {
            "policy_key": "encryption_standard_2026",
            "policy_value": {"algorithm": "ChaCha20-Poly1305"},
        },
        format="json",
    )
    assert res_pol.status_code == 201

    res_rep = c_sec.get("/api/v1/badms/reports/department/?department=CSE")
    assert res_rep.status_code == 200
    assert res_rep.json()["department"] == "CSE"

    res_sec_audit = c_sec.get("/api/v1/badms/audit-logs/security/")
    assert res_sec_audit.status_code == 200


def test_backup_and_archival_detail_api(stub_iam):
    rec = BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="records_db",
        status="success",
        file_path="/tmp/rec.dump",
        file_size_bytes=500,
        checksum_sha256="abc12345",
        triggered_by_user_id=1001,
    )
    arch = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="proj.tar",
        file_type="tar",
        file_size_bytes=2000,
        file_storage_path="/tmp/proj.tar",
        status="submitted",
    )

    c = _client(
        stub_iam,
        user_id=1001,
        roles=("student",),
        active_role="student",
        modules=("badms",),
        permissions=("badms.backup.view", "badms.archival.view"),
    )
    res_b = c.get(f"/api/v1/badms/backups/{rec.id}/")
    assert res_b.status_code == 200
    assert res_b.json()["id"] == rec.id

    res_a = c.get(f"/api/v1/badms/archival-requests/{arch.id}/")
    assert res_a.status_code == 200
    assert res_a.json()["id"] == arch.id


def test_local_schedule_create_and_update_api(stub_iam):
    c = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.view", "badms.backup.manage"),
    )

    res_create = c.post(
        "/api/v1/badms/schedules/local/",
        {
            "name": "Local Lab Backup",
            "dataset_name": "lab_workstation",
            "cron_expression": "0 22 * * 1-5",
        },
    )
    assert res_create.status_code == 201
    sched_id = res_create.json()["id"]
    assert res_create.json()["scope_type"] == "local"

    res_patch = c.patch(
        f"/api/v1/badms/schedules/local/{sched_id}/",
        {"cron_expression": "0 23 * * 1-5"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["cron_expression"] == "0 23 * * 1-5"


def test_rejections_and_special_archival_api(stub_iam):
    # 1. Archival Rejection
    arch = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="junk.tar",
        file_type="tar",
        file_size_bytes=1000,
        file_storage_path="/tmp/junk.tar",
        status="submitted",
    )
    c_hod = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.approve", "badms.storage.approve"),
    )
    res_arch_rej = c_hod.post(
        f"/api/v1/badms/archival-requests/{arch.id}/decide/",
        {"decision": "reject", "remarks": "Invalid format"},
    )
    assert res_arch_rej.status_code == 200
    assert res_arch_rej.json()["status"] == "rejected"

    # 2. Storage Extension Rejection
    ext = StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Unjustified request",
        status="submitted",
    )
    res_ext_rej = c_hod.post(
        f"/api/v1/badms/storage-extensions/{ext.id}/decide/",
        {"decision": "reject", "remarks": "No budget"},
    )
    assert res_ext_rej.status_code == 200
    assert res_ext_rej.json()["status"] == "rejected"

    # 3. Restoration Rejection
    rest = RestorationRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        archival_request_id=arch.id,
        classification="Sensitive",
        target_destination="/tmp/rest",
        status="sensitive_pending_approval",
    )
    c_sys = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.restoration.view", "badms.restoration.approve"),
    )
    res_rest_rej = c_sys.post(
        f"/api/v1/badms/restorations/{rest.id}/approve/",
        {"decision": "reject"},
    )
    assert res_rest_rej.status_code == 200
    assert res_rest_rej.json()["status"] == "rejected"

    # 4. Super Admin Special Archival
    c_super = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.manage"),
    )
    res_spec = c_super.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "file_name": "special_audit.iso",
            "file_type": "iso",
            "file_size_bytes": 10000000,
            "reason": "Institutional Accreditation Complete Snapshot",
            "file_storage_path": "/special/special_audit.iso",
        },
    )
    assert res_spec.status_code == 201
    assert res_spec.json()["status"] == "special_archived"
