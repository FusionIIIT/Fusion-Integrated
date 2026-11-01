"""Tests for BADMS Backup Management (Phase 7)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    BackupExecution,
    BackupScope,
    BackupStatus,
    BackupType,
    BadmsAuditLog,
    BadmsNotification,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


def test_sysadmin_can_trigger_manual_local_backup(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_CREATE, p.BACKUP_VIEW),
    )

    payload = {
        "backup_type": "full",
        "scope": "local",
        "target_dataset": "student_records",
    }
    res = client.post("/api/v1/badms/backups/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["status"] == BackupStatus.COMPLETED
    assert data["scope"] == BackupScope.LOCAL
    assert data["repository_reachable"] is True
    assert data["integrity_verified"] is True
    assert len(data["checksum"]) == 64
    assert data["size_bytes"] > 0

    # Audit log check
    audit = BadmsAuditLog.objects.filter(
        target_id=str(data["id"]), action="badms.backup.execute"
    ).first()
    assert audit is not None
    assert audit.outcome == "success"

    # Notification check
    notif = BadmsNotification.objects.filter(
        recipient_role="sysadmin", notification_type="backup_completed"
    ).first()
    assert notif is not None
    assert "Completed Successfully" in notif.subject


def test_repository_unreachable_fails_and_notifies_sysadmin(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_CREATE, p.BACKUP_VIEW),
    )

    payload = {
        "backup_type": "full",
        "scope": "local",
        "simulate_unreachable": True,
    }
    res = client.post("/api/v1/badms/backups/", payload, format="json")
    assert res.status_code == 200

    data = res.data
    assert data["status"] == BackupStatus.FAILED
    assert data["repository_reachable"] is False
    assert "unreachable" in data["error_message"].lower()

    # Verify SysAdmin failure alert
    failure_notif = BadmsNotification.objects.filter(
        recipient_role="sysadmin", notification_type="backup_failure"
    ).first()
    assert failure_notif is not None
    assert "FAILED" in failure_notif.subject


def test_escalation_to_director_of_it_after_three_consecutive_failures(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_CREATE, p.BACKUP_VIEW),
    )

    # Failure 1
    res1 = client.post(
        "/api/v1/badms/backups/", {"simulate_failure": True}, format="json"
    )
    assert res1.data["consecutive_failure_count"] == 1
    assert not BadmsNotification.objects.filter(
        recipient_role="director_of_it"
    ).exists()

    # Failure 2
    res2 = client.post(
        "/api/v1/badms/backups/", {"simulate_failure": True}, format="json"
    )
    assert res2.data["consecutive_failure_count"] == 2
    assert not BadmsNotification.objects.filter(
        recipient_role="director_of_it"
    ).exists()

    # Failure 3 -> triggers escalation to Director of IT
    res3 = client.post(
        "/api/v1/badms/backups/", {"simulate_failure": True}, format="json"
    )
    assert res3.data["consecutive_failure_count"] == 3

    director_escalation = BadmsNotification.objects.filter(
        recipient_role="director_of_it", notification_type="director_escalation"
    ).first()
    assert director_escalation is not None
    assert "CRITICAL ESCALATION" in director_escalation.subject
    assert "3 consecutive backup executions" in director_escalation.message


def test_success_resets_consecutive_failure_counter(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_CREATE, p.BACKUP_VIEW),
    )

    # 2 failures
    client.post("/api/v1/badms/backups/", {"simulate_failure": True}, format="json")
    client.post("/api/v1/badms/backups/", {"simulate_failure": True}, format="json")

    # 1 success
    res = client.post(
        "/api/v1/badms/backups/", {"backup_type": "full"}, format="json"
    )
    assert res.status_code == 201
    assert res.data["consecutive_failure_count"] == 0


def test_superadmin_can_trigger_global_backup(stub_iam):
    client = _client(
        stub_iam,
        user_id=1,
        kind="staff",
        active_role="Super Admin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE, p.POLICY_MANAGE),
    )

    payload = {"backup_type": "full", "scope": "global", "target_dataset": "all"}
    res = client.post("/api/v1/badms/backups/", payload, format="json")
    assert res.status_code == 201
    assert res.data["scope"] == "global"


def test_non_superadmin_cannot_trigger_global_backup(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_CREATE, p.BACKUP_VIEW),  # Missing policy.manage
    )

    payload = {"backup_type": "full", "scope": "global"}
    res = client.post("/api/v1/badms/backups/", payload, format="json")
    assert res.status_code == 403


def test_backup_history_and_integrity_verification(stub_iam):
    b_local = BackupExecution.objects.create(
        scope=BackupScope.LOCAL,
        status=BackupStatus.COMPLETED,
        checksum="a" * 64,
        integrity_verified=True,
    )
    b_global = BackupExecution.objects.create(
        scope=BackupScope.GLOBAL,
        status=BackupStatus.COMPLETED,
        checksum="b" * 64,
        integrity_verified=True,
    )

    # SysAdmin with BACKUP_VIEW sees only local
    c_local = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_VIEW,),
    )
    res = c_local.get("/api/v1/badms/backups/")
    assert res.status_code == 200
    ids = [r["id"] for r in res.data["results"]]
    assert b_local.pk in ids
    assert b_global.pk not in ids

    # Super Admin with BACKUP_MANAGE sees both
    c_admin = _client(
        stub_iam,
        user_id=1,
        kind="staff",
        active_role="Super Admin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE,),
    )
    res_admin = c_admin.get("/api/v1/badms/backups/")
    assert res_admin.status_code == 200
    ids_admin = {r["id"] for r in res_admin.data["results"]}
    assert {b_local.pk, b_global.pk}.issubset(ids_admin)

    # Integrity verification
    verify_res = c_admin.post(f"/api/v1/badms/backups/{b_local.pk}/verify/")
    assert verify_res.status_code == 200
    assert verify_res.data["integrity_verified"] is True
