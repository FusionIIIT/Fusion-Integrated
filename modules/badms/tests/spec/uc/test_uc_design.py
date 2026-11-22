"""Executable coverage of the frozen BADMS use-case design."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RestorationRequest,
    StorageExtensionRequest,
    UserStorageQuota,
)
from modules.badms.services.audit import log_audit_event
from modules.badms.tasks import evaluate_and_dispatch_due_backups, monitor_storage_thresholds

pytestmark = pytest.mark.django_db


@dataclass
class Actor:
    user_id: int
    active_role: str = "student"
    department: str = "CSE"


def _client(stub_iam, **kwargs):
    stub_iam(make_session(**kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-design")
    return client


def _archival_request(*, requester_id=1001, department="CSE", status="submitted", **kwargs):
    return ArchivalRequest.objects.create(
        requester_user_id=requester_id,
        department=department,
        file_name="research.tar",
        file_type="tar",
        file_size_bytes=1024,
        reason="UC design fixture",
        file_storage_path="/archive/research.tar",
        status=status,
        **kwargs,
    )


def test_uc_design_001_ba_uc_001_trigger_manual_backup(stub_iam):
    """test_id: UC-DESIGN-001; source_id: BA-UC-001."""
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.manage",),
    )

    response = client.post("/api/v1/badms/backups/manual/", {"dataset_name": "uc_manual"})

    assert response.status_code == 201
    record = BackupRecord.objects.get(pk=response.json()["id"])
    assert record.backup_type == BackupRecord.TYPE_MANUAL
    assert record.status == BackupRecord.STATUS_SUCCESS


def test_uc_design_002_ba_uc_002_submit_secure_archival_request(stub_iam):
    """test_id: UC-DESIGN-002; source_id: BA-UC-002."""
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.archival.create",),
    )

    response = client.post(
        "/api/v1/badms/archival-requests/",
        {
            "department": "CSE",
            "file_name": "thesis.tar",
            "file_type": "tar",
            "file_size_bytes": 1024,
            "reason": "Research retention",
            "file_storage_path": "/uploads/thesis.tar",
            "initial_classification": "Routine",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "submitted"
    assert response.json()["file_name"] == "thesis.tar"


def test_uc_design_003_ba_uc_003_decide_secure_archival_request(stub_iam):
    """test_id: UC-DESIGN-003; source_id: BA-UC-003."""
    own_request = _archival_request()
    foreign_request = _archival_request(requester_id=2002, department="ECE")
    client = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.approve",),
    )

    approved = client.post(
        f"/api/v1/badms/archival-requests/{own_request.id}/decide/",
        {"decision": "approve", "remarks": "Approved"},
    )
    before_refusal = (foreign_request.status, foreign_request.hod_reviewed_by_user_id)
    refused = client.post(
        f"/api/v1/badms/archival-requests/{foreign_request.id}/decide/",
        {"decision": "approve", "remarks": "Out of scope"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "hod_approved"
    assert refused.status_code == 404
    foreign_request.refresh_from_db()
    assert (foreign_request.status, foreign_request.hod_reviewed_by_user_id) == before_refusal


def test_uc_design_004_ba_uc_004_classify_secure_archival_data(stub_iam):
    """test_id: UC-DESIGN-004; source_id: BA-UC-004."""
    request = _archival_request(status="hod_approved")
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.review",),
    )

    response = client.post(
        f"/api/v1/badms/archival-requests/{request.id}/classify/",
        {"classification": "Critical"},
    )

    assert response.status_code == 200
    assert response.json()["authoritative_classification"] == "Critical"
    assert response.json()["status"] == "classified_non_sensitive"


def test_uc_design_005_ba_uc_005_configure_sensitive_data_encryption(stub_iam):
    """test_id: UC-DESIGN-005; source_id: BA-UC-005."""
    request = _archival_request(
        status="classified_sensitive", authoritative_classification="Sensitive"
    )
    client = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.security.manage",),
    )

    response = client.post(
        f"/api/v1/badms/archival-requests/{request.id}/configure-encryption/",
        {"encryption_algorithm": "AES-256-GCM"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sensitive_archive_encrypted"
    assert response.json()["is_encrypted"] is True


def test_uc_design_006_ba_uc_006_execute_scheduled_automatic_backup():
    """test_id: UC-DESIGN-006; source_id: BA-UC-006."""
    schedule = BackupSchedule.objects.create(
        name="UC due schedule",
        scope_type="global",
        dataset_name="uc_scheduled_db",
        cron_expression="0 2 * * *",
        created_by_user_id=1,
        effective_from=datetime.now(UTC) - timedelta(days=1),
    )

    result = evaluate_and_dispatch_due_backups()

    schedule.refresh_from_db()
    assert result["dispatched"] == 1
    assert schedule.last_run_at is not None
    assert BackupRecord.objects.filter(
        dataset_name="uc_scheduled_db", backup_type=BackupRecord.TYPE_SCHEDULED
    ).exists()


def test_uc_design_007_ba_uc_007_submit_storage_extension_request(stub_iam):
    """test_id: UC-DESIGN-007; source_id: BA-UC-007."""
    UserStorageQuota.objects.create(
        user_id=1001, allocated_quota_bytes=1000, used_storage_bytes=1000, is_full=True
    )
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.storage.create",),
    )

    response = client.post(
        "/api/v1/badms/storage-extensions/",
        {"department": "CSE", "requested_extension_bytes": 500, "justification": "Dataset"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "submitted"
    assert response.json()["current_usage_bytes"] == 1000


def test_uc_design_008_ba_uc_008_decide_storage_extension_request(stub_iam):
    """test_id: UC-DESIGN-008; source_id: BA-UC-008."""
    UserStorageQuota.objects.create(
        user_id=1001, allocated_quota_bytes=1000, used_storage_bytes=1000, is_full=True
    )
    request = StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Dataset",
    )
    client = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.storage.approve",),
    )

    response = client.post(
        f"/api/v1/badms/storage-extensions/{request.id}/decide/",
        {"decision": "approve", "remarks": "Approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert UserStorageQuota.objects.get(user_id=1001).allocated_quota_bytes == 1500


def test_uc_design_009_ba_uc_009_configure_local_backup_schedule(stub_iam):
    """test_id: UC-DESIGN-009; source_id: BA-UC-009."""
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.manage",),
    )

    created = client.post(
        "/api/v1/badms/schedules/local/",
        {"name": "Lab backup", "dataset_name": "lab_db", "cron_expression": "0 2 * * *"},
    )
    updated = client.patch(
        f"/api/v1/badms/schedules/local/{created.json()['id']}/",
        {"cron_expression": "0 3 * * *"},
    )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["scope_type"] == "local"
    assert updated.json()["cron_expression"] == "0 3 * * *"


def test_uc_design_010_ba_uc_010_perform_special_archival_operation(stub_iam):
    """test_id: UC-DESIGN-010; source_id: BA-UC-010."""
    client = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.archival.manage",),
    )

    response = client.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "file_name": "sensitive_research.tar",
            "file_type": "tar",
            "file_size_bytes": 4096,
            "reason": "Authority-directed extended storage",
            "file_storage_path": "/special/research.tar",
            "classification": "Sensitive",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "special_archived"
    assert response.json()["is_special_archival"] is True


@pytest.mark.skip(
    reason="NOT_AUTOMATED: global default backup-policy settings are not modeled or exposed."
)
def test_uc_design_011_ba_uc_011_define_global_backup_schedules_and_defaults():
    """test_id: UC-DESIGN-011; source_id: BA-UC-011."""


def test_uc_design_012_ba_uc_012_view_audit_logs_and_activity_history(stub_iam):
    """test_id: UC-DESIGN-012; source_id: BA-UC-012."""
    AuditEvent.objects.create(
        event_type="manual_backup_created",
        actor_user_id=6001,
        actor_role="SysAdmin",
        target_model="BackupRecord",
        target_id=1,
        department="Central",
    )
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.audit.view",),
    )

    response = client.get("/api/v1/badms/audit-logs/")

    assert response.status_code == 200
    assert response.json()["results"][0]["event_type"] == "manual_backup_created"


def test_uc_design_013_ba_uc_013_review_security_audit_activity(stub_iam):
    """test_id: UC-DESIGN-013; source_id: BA-UC-013."""
    AuditEvent.objects.create(
        event_type="archival_encryption_configured",
        actor_user_id=7001,
        actor_role="IT Security",
        target_model="ArchivalRequest",
        target_id=1,
        department="CSE",
    )
    client = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.audit.view",),
    )

    response = client.get("/api/v1/badms/audit-logs/security/")

    assert response.status_code == 200
    assert response.json()["results"][0]["event_type"] == "archival_encryption_configured"


def test_uc_design_014_ba_uc_014_view_backup_history_and_status(stub_iam):
    """test_id: UC-DESIGN-014; source_id: BA-UC-014."""
    own = BackupRecord.objects.create(
        backup_type="manual",
        dataset_name="own_backup",
        status="success",
        triggered_by_user_id=1001,
    )
    BackupRecord.objects.create(
        backup_type="manual",
        dataset_name="other_backup",
        status="success",
        triggered_by_user_id=2002,
    )
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.backup.view",),
    )

    response = client.get("/api/v1/badms/backups/")

    assert response.status_code == 200
    assert [record["id"] for record in response.json()["results"]] == [own.id]
    assert response.json()["results"][0]["status"] == "success"


def test_uc_design_015_ba_uc_015_track_archival_request_status(stub_iam):
    """test_id: UC-DESIGN-015; source_id: BA-UC-015."""
    own = _archival_request(status="hod_approved")
    _archival_request(requester_id=2002, department="ECE", status="submitted")
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.archival.view",),
    )

    response = client.get("/api/v1/badms/archival-requests/")

    assert response.status_code == 200
    assert [request["id"] for request in response.json()["results"]] == [own.id]
    assert response.json()["results"][0]["status"] == "hod_approved"


def test_uc_design_016_ba_uc_016_request_data_restoration(stub_iam):
    """test_id: UC-DESIGN-016; source_id: BA-UC-016."""
    archive = _archival_request(
        status="classified_non_sensitive", authoritative_classification="Routine"
    )
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.restoration.create",),
    )

    response = client.post(
        "/api/v1/badms/restorations/",
        {"archival_request_id": archive.id, "target_destination": "/restore/research"},
    )

    assert response.status_code == 201
    assert response.json()["archival_request_id"] == archive.id
    assert response.json()["status"] == "requested_standard"


def test_uc_design_017_ba_uc_017_approve_sensitive_data_restoration(stub_iam):
    """test_id: UC-DESIGN-017; source_id: BA-UC-017."""
    request = RestorationRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        archival_request_id=1,
        classification="Sensitive",
        target_destination="/restore/sensitive",
        status="sensitive_pending_approval",
    )
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.restoration.approve",),
    )

    response = client.post(
        f"/api/v1/badms/restorations/{request.id}/approve/", {"decision": "approve"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_by_user_id"] == 6001


def test_uc_design_018_ba_uc_018_execute_data_restoration(stub_iam):
    """test_id: UC-DESIGN-018; source_id: BA-UC-018."""
    request = RestorationRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        archival_request_id=1,
        classification="Sensitive",
        target_destination="/restore/sensitive",
        status="approved",
        approved_by_user_id=6001,
    )
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.restoration.restore",),
    )

    response = client.post(f"/api/v1/badms/restorations/{request.id}/execute/", {})

    assert response.status_code == 200
    assert response.json()["status"] == "restored"
    assert response.json()["executed_by_user_id"] == 6001


@pytest.mark.skip(
    reason="NOT_AUTOMATED: central IAM Administration Console is outside BADMS test control."
)
def test_uc_design_019_ba_uc_019_manage_rbac_permissions():
    """test_id: UC-DESIGN-019; source_id: BA-UC-019."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: security-policy enforcement is not implemented or exposed."
)
def test_uc_design_020_ba_uc_020_define_and_enforce_security_policies():
    """test_id: UC-DESIGN-020; source_id: BA-UC-020."""


def test_uc_design_021_ba_uc_021_view_department_data_management_reports(stub_iam):
    """test_id: UC-DESIGN-021; source_id: BA-UC-021."""
    _archival_request(department="CSE")
    StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Dataset",
    )
    client = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.report.view",),
    )

    response = client.get("/api/v1/badms/reports/department/?department=CSE")

    assert response.status_code == 200
    assert response.json()["department"] == "CSE"
    assert response.json()["total_archival_requests"] == 1
    assert response.json()["total_storage_extensions"] == 1


def test_uc_design_022_ba_uc_022_monitor_storage_thresholds():
    """test_id: UC-DESIGN-022; source_id: BA-UC-022."""
    quota = UserStorageQuota.objects.create(
        user_id=9001, allocated_quota_bytes=1000, used_storage_bytes=1000, is_full=False
    )

    result = monitor_storage_thresholds()

    quota.refresh_from_db()
    assert result["updated"] == 1
    assert quota.is_full is True


def test_uc_design_023_ba_uc_023_record_audit_event():
    """test_id: UC-DESIGN-023; source_id: BA-UC-023."""
    actor = Actor(user_id=7001, active_role="IT Security", department="Central")

    event = log_audit_event(
        "security_access_reviewed",
        actor,
        "SecurityPolicy",
        target_id=42,
        details={"outcome": "reviewed"},
    )

    persisted = AuditEvent.objects.get(pk=event.id)
    assert persisted.actor_user_id == 7001
    assert persisted.actor_role == "IT Security"
    assert persisted.details == {"outcome": "reviewed"}
