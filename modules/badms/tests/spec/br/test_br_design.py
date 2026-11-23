"""Executable coverage for the frozen BADMS business-rule design."""

from dataclasses import dataclass
from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.badms.domain import retention, schedules
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RetentionPolicy,
    StorageExtensionRequest,
    UserStorageQuota,
)
from modules.badms.services import archival, backups, restoration, storage

pytestmark = pytest.mark.django_db


@dataclass
class Actor:
    user_id: int
    active_role: str = "student"
    department: str = "CSE"
    roles: tuple[str, ...] = ()


def _client(stub_iam, **kwargs):
    stub_iam(make_session(**kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token br-design")
    return client


def _request(*, requester=1001, department="CSE", status="submitted", classification="Routine"):
    return ArchivalRequest.objects.create(
        requester_user_id=requester,
        department=department,
        file_name="research.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="BR design fixture",
        file_storage_path="/archive/research.tar",
        initial_classification=classification,
        authoritative_classification=classification if status != "submitted" else "",
        status=status,
    )


def _hod(user_id=5001, department="CSE"):
    return Actor(user_id, "HOD", department, (f"HOD ({department})",))


def _sysadmin(user_id=6001):
    return Actor(user_id, "SysAdmin", "Central", ("SysAdmin",))


def _security(user_id=7001):
    return Actor(user_id, "IT Security", "Central", ("IT Security",))


def test_br_design_001_br_ba_001_manual_backup_authorization(stub_iam):
    """BR-DESIGN-001; source_id: BR-BA-001."""
    before = BackupRecord.objects.count()
    refused = _client(stub_iam, user_id=1001, modules=("badms",), permissions=())
    assert refused.post("/api/v1/badms/backups/manual/", {"dataset_name": "denied"}).status_code == 403
    assert BackupRecord.objects.count() == before
    for role, user_id in (("SysAdmin", 6001), ("Super Admin", 1)):
        allowed = _client(
            stub_iam, user_id=user_id, roles=(role,), active_role=role,
            modules=("badms",), permissions=("badms.backup.manage",),
        )
        assert allowed.post("/api/v1/badms/backups/manual/", {"dataset_name": role}).status_code == 201


def test_br_design_002_br_ba_002_respective_hod_approval(stub_iam):
    """BR-DESIGN-002; source_id: BR-BA-002."""
    req = _request()
    foreign = _client(
        stub_iam, user_id=5002, roles=("HOD (ECE)",), active_role="HOD (ECE)",
        modules=("badms",), permissions=("badms.archival.approve",),
    )
    response = foreign.post(f"/api/v1/badms/archival-requests/{req.id}/decide/", {"decision": "approve"})
    assert response.status_code == 404
    req.refresh_from_db()
    assert req.status == "submitted"
    assert req.hod_reviewed_by_user_id is None


def test_br_design_003_br_ba_003_it_security_encryption_authority(stub_iam):
    """BR-DESIGN-003; source_id: BR-BA-003."""
    req = _request(status="classified_sensitive", classification="Sensitive")
    before = (req.status, req.is_encrypted, req.encrypted_by_user_id)
    unauthorized = _client(stub_iam, user_id=6001, modules=("badms",), permissions=())
    assert unauthorized.post(f"/api/v1/badms/archival-requests/{req.id}/configure-encryption/", {}).status_code == 403
    req.refresh_from_db()
    assert (req.status, req.is_encrypted, req.encrypted_by_user_id) == before
    authorized = _client(
        stub_iam, user_id=7001, roles=("IT Security",), active_role="IT Security",
        modules=("badms",), permissions=("badms.security.manage",),
    )
    assert authorized.post(f"/api/v1/badms/archival-requests/{req.id}/configure-encryption/", {}).status_code == 200


def test_br_design_004_br_ba_004_sysadmin_authoritative_classification(stub_iam):
    """BR-DESIGN-004; source_id: BR-BA-004."""
    req = _request(status="hod_approved", classification="")
    unauthorized = _client(stub_iam, user_id=5001, modules=("badms",), permissions=())
    assert unauthorized.post(f"/api/v1/badms/archival-requests/{req.id}/classify/", {"classification": "Sensitive"}).status_code == 403
    req.refresh_from_db()
    assert req.authoritative_classification == ""
    allowed = _client(
        stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin",
        modules=("badms",), permissions=("badms.archival.review",),
    )
    assert allowed.post(f"/api/v1/badms/archival-requests/{req.id}/classify/", {"classification": "Sensitive"}).status_code == 200


def test_br_design_005_br_ba_005_sensitive_restoration_requires_approval(stub_iam):
    """BR-DESIGN-005; source_id: BR-BA-005."""
    archive = _request(status="sensitive_archive_encrypted", classification="Sensitive")
    restore = restoration.request_data_restoration(Actor(1001), archive.id, "/restore/sensitive")
    client = _client(stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin", modules=("badms",), permissions=("badms.restoration.restore", "badms.restoration.approve"))
    refused = client.post(f"/api/v1/badms/restorations/{restore.id}/execute/", {})
    assert refused.status_code == 409
    restore.refresh_from_db()
    assert restore.status == "sensitive_pending_approval" and restore.restored_at is None
    assert client.post(f"/api/v1/badms/restorations/{restore.id}/approve/", {"decision": "approve"}).status_code == 200
    assert client.post(f"/api/v1/badms/restorations/{restore.id}/execute/", {}).status_code == 200


def test_br_design_006_br_ba_006_initial_classification_default():
    """BR-DESIGN-006; source_id: BR-BA-006."""
    explicit = archival.submit_archival_request(Actor(1001), "explicit.tar", "tar", 10, "x", "/x", "Critical")
    defaulted = archival.submit_archival_request(Actor(1002), "default.tar", "tar", 10, "x", "/x", "")
    assert explicit.initial_classification == "Critical"
    assert defaulted.initial_classification == "Routine"


@pytest.mark.skip(reason="NOT_AUTOMATED: encryption in transit is not exposed by the BADMS API or model.")
def test_br_design_007_br_ba_007_sensitive_data_encryption():
    """BR-DESIGN-007; source_id: BR-BA-007."""


def test_br_design_008_br_ba_008_retention_by_classification():
    """BR-DESIGN-008; source_id: BR-BA-008."""
    for classification, days in (("Routine", 31), ("Sensitive", 366), ("Critical", 1001), ("Archival", 2001)):
        RetentionPolicy.objects.create(name=f"{classification} policy", data_classification=classification, retention_days=days, configured_by_user_id=7001)
    approved = archival.decide_archival_request(_hod(), _request().id, "approve")
    classified = archival.classify_archival_request(_sysadmin(), approved.id, "Sensitive")
    assert classified.retention_policy_ref == "Sensitive policy (366d)"
    assert retention.resolve_retention_duration("Sensitive", 366) == 366


def test_br_design_009_br_ba_009_hod_storage_approval(stub_iam):
    """BR-DESIGN-009; source_id: BR-BA-009."""
    UserStorageQuota.objects.create(user_id=1001, allocated_quota_bytes=100, used_storage_bytes=100, is_full=True)
    req = storage.submit_storage_extension(Actor(1001), 50, "research")
    admin = _client(stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin", modules=("badms",), permissions=())
    assert admin.post(f"/api/v1/badms/storage-extensions/{req.id}/decide/", {"decision": "approve"}).status_code == 403
    req.refresh_from_db()
    assert req.status == "submitted" and req.hod_reviewed_by_user_id is None


def test_br_design_010_br_ba_010_hod_department_scope(stub_iam):
    """BR-DESIGN-010; source_id: BR-BA-010."""
    client = _client(stub_iam, user_id=5001, roles=("HOD (CSE)",), active_role="HOD (CSE)", modules=("badms",), permissions=("badms.report.view",))
    assert client.get("/api/v1/badms/reports/department/?department=CSE").status_code == 200
    assert client.get("/api/v1/badms/reports/department/?department=ECE").status_code == 404


def test_br_design_011_br_ba_011_local_schedule_overrides_global():
    """BR-DESIGN-011; source_id: BR-BA-011."""
    global_schedule = {"cron": "0 1 * * *", "is_active": True}
    local_schedule = {"cron": "0 2 * * *", "is_active": True}
    assert schedules.resolve_effective_schedule(local_schedule, global_schedule) == local_schedule
    assert schedules.resolve_effective_schedule(None, global_schedule) == global_schedule


def test_br_design_012_br_ba_012_schedule_parameter_validation(stub_iam):
    """BR-DESIGN-012; source_id: BR-BA-012."""
    client = _client(stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin", modules=("badms",), permissions=("badms.backup.manage",))
    before = BackupSchedule.objects.count()
    response = client.post("/api/v1/badms/schedules/local/", {"name": "bad", "dataset_name": "db", "cron_expression": "invalid"})
    assert response.status_code == 400
    assert BackupSchedule.objects.count() == before


def test_br_design_013_br_ba_013_scheduled_repository_reachability():
    """BR-DESIGN-013; source_id: BR-BA-013."""
    reachable = backups.execute_scheduled_backup("reachable", repository_reachable=True)
    unreachable = backups.execute_scheduled_backup("unreachable", repository_reachable=False)
    assert reachable.status == BackupRecord.STATUS_SUCCESS
    assert unreachable.status == BackupRecord.STATUS_FAILURE
    assert unreachable.file_path == ""


def test_br_design_014_br_ba_014_backup_failure_alert_sla():
    """BR-DESIGN-014; source_id: BR-BA-014."""
    failure = backups.execute_scheduled_backup("sla", simulate_failure=True)
    alert = AuditEvent.objects.get(event_type="backup_failure_alert_sent", target_id=failure.id)
    assert alert.details["recipient_role"] == "SysAdmin"
    assert alert.timestamp - failure.completed_at <= timedelta(minutes=5)


def test_br_design_015_br_ba_015_repeated_failure_escalation():
    """BR-DESIGN-015; source_id: BR-BA-015."""
    failures = [backups.execute_scheduled_backup("escalation", simulate_failure=True) for _ in range(3)]
    escalation = AuditEvent.objects.get(event_type="backup_failure_escalated", target_id=failures[-1].id)
    assert failures[-1].consecutive_failure_count == 3
    assert escalation.details["recipient_role"] == "Director of IT"


def test_br_design_016_br_ba_016_storage_usage_validation():
    """BR-DESIGN-016; source_id: BR-BA-016."""
    quota = UserStorageQuota.objects.create(user_id=1001, allocated_quota_bytes=100, used_storage_bytes=99, is_full=False)
    before = StorageExtensionRequest.objects.count()
    with pytest.raises(ConflictError) as exc_info:
        storage.submit_storage_extension(Actor(1001), 50, "too early")
    assert "not full" in str(exc_info.value)
    assert StorageExtensionRequest.objects.count() == before
    quota.used_storage_bytes = quota.allocated_quota_bytes
    quota.is_full = True
    quota.save()
    assert storage.submit_storage_extension(Actor(1001), 50, "at quota").current_usage_bytes == 100


@pytest.mark.skip(reason="NOT_AUTOMATED: infrastructure availability and departmental policy review are not modeled or exposed.")
def test_br_design_017_br_ba_017_storage_decision_criteria():
    """BR-DESIGN-017; source_id: BR-BA-017."""


def test_br_design_018_br_ba_018_special_archival_super_admin_authority(stub_iam):
    """BR-DESIGN-018; source_id: BR-BA-018."""
    before = ArchivalRequest.objects.filter(is_special_archival=True).count()
    denied = _client(stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin", modules=("badms",), permissions=())
    payload = {"file_name": "special.tar", "file_type": "tar", "file_size_bytes": 10, "reason": "offline", "file_storage_path": "/special.tar", "classification": "Sensitive"}
    assert denied.post("/api/v1/badms/archival-requests/special/", payload).status_code == 403
    assert ArchivalRequest.objects.filter(is_special_archival=True).count() == before
    allowed = _client(stub_iam, user_id=1, roles=("Super Admin",), active_role="Super Admin", modules=("badms",), permissions=("badms.archival.manage",))
    assert allowed.post("/api/v1/badms/archival-requests/special/", payload).status_code == 201


def test_br_design_019_br_ba_019_super_admin_global_backup_authority(stub_iam):
    """BR-DESIGN-019; source_id: BR-BA-019."""
    payload = {"name": "global", "dataset_name": "db", "cron_expression": "0 1 * * *"}
    before = BackupSchedule.objects.count()
    denied = _client(stub_iam, user_id=6001, roles=("SysAdmin",), active_role="SysAdmin", modules=("badms",), permissions=())
    assert denied.post("/api/v1/badms/schedules/global/", payload).status_code == 403
    assert BackupSchedule.objects.count() == before
    allowed = _client(stub_iam, user_id=1, roles=("Super Admin",), active_role="Super Admin", modules=("badms",), permissions=("badms.backup_policy.manage",))
    assert allowed.post("/api/v1/badms/schedules/global/", payload).status_code == 201


def test_br_design_020_br_ba_020_protected_information_scope(stub_iam):
    """BR-DESIGN-020; source_id: BR-BA-020."""
    own = BackupRecord.objects.create(backup_type="manual", dataset_name="own", status="success", triggered_by_user_id=1001)
    BackupRecord.objects.create(backup_type="manual", dataset_name="other", status="success", triggered_by_user_id=1002)
    client = _client(stub_iam, user_id=1001, modules=("badms",), permissions=("badms.backup.view",))
    response = client.get("/api/v1/badms/backups/")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [own.id]


@pytest.mark.skip(reason="NOT_AUTOMATED: central IAM RBAC administration is outside BADMS and no security-policy enforcement endpoint is exposed.")
def test_br_design_021_br_ba_021_it_security_rbac_authority():
    """BR-DESIGN-021; source_id: BR-BA-021."""
