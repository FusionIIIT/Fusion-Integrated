from datetime import date, time, timezone as dt_tz
from io import BytesIO
from unittest.mock import MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchiveRequest,
    AuditEvent,
    BackupRun,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    StorageExtensionRequest,
    StorageThreshold,
)
from modules.badms.services import backups
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id=4101, permissions=(), kind="student", role="student", dept="CSE"):
    UserRef.objects.update_or_create(
        user_id=user_id,
        defaults={
            "username": f"user-{user_id}",
            "display_name": f"User {user_id}",
            "kind": kind,
            "email": f"user{user_id}@example.test",
            "department": dept,
            "is_active": True,
        },
    )
    session = make_session(
        user_id=user_id,
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=("badms",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token test-{user_id}")
    return client


@override_settings(DEBUG=True)
def test_archive_requests_full_lifecycle(stub_iam):
    SecurityPolicy.objects.update_or_create(
        id=1,
        defaults={
            "retention_days": {
                "Critical": 3650,
                "Sensitive": 1825,
                "Routine": 730,
                "Archival": 365,
            }
        },
    )
    student = _client(
        stub_iam,
        user_id=101,
        permissions=("badms.archive.create", "badms.archive.view_self"),
        kind="student",
        dept="CSE",
    )
    upload = SimpleUploadedFile("dataset.csv", b"col1,col2\n1,2\n", content_type="text/csv")
    resp = student.post(
        "/api/v1/badms/archive_requests",
        {
            "file_name": "dataset.csv",
            "file_date": "2026-11-20",
            "owners": "Student A",
            "file_type": "text/csv",
            "reason": "Lab dataset",
            "initial_classification": "Routine",
            "attachment": upload,
        },
        format="multipart",
    )
    assert resp.status_code == 201, resp.data
    archive_id = resp.data["id"]
    assert resp.data["status"] == "Submitted"

    resp = student.get("/api/v1/badms/archive_requests")
    assert resp.status_code == 200
    assert any(r["id"] == archive_id for r in resp.data["results"])

    resp = student.get(f"/api/v1/badms/archive_requests/{archive_id}")
    assert resp.status_code == 200
    assert resp.data["id"] == archive_id

    hod = _client(
        stub_iam,
        user_id=201,
        permissions=("badms.archive.review_department",),
        kind="faculty",
        role="Department Head (HoD)",
        dept="CSE",
    )
    resp = hod.get("/api/v1/badms/archive_requests")
    assert resp.status_code == 200

    resp = hod.post(
        f"/api/v1/badms/archive_requests/{archive_id}/decision",
        {"decision": "approve", "note": "Approved by HoD"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "HoD Approved"

    sysadmin = _client(
        stub_iam,
        user_id=301,
        permissions=("badms.archive.classify",),
        kind="staff",
        role="System Administrator (SysAdmin)",
        dept="IT",
    )
    resp = sysadmin.post(
        f"/api/v1/badms/archive_requests/{archive_id}/classification",
        {"classification": "Sensitive"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Classified Sensitive / Routed to IT Security"

    security = _client(
        stub_iam,
        user_id=401,
        permissions=("badms.archive.encrypt",),
        kind="staff",
        role="IT Security Team",
        dept="IT",
    )
    resp = security.post(
        f"/api/v1/badms/archive_requests/{archive_id}/encryption",
        {},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Sensitive Archive Encrypted"


@override_settings(DEBUG=True)
def test_archive_requests_rejection_flow(stub_iam):
    student = _client(
        stub_iam,
        user_id=105,
        permissions=("badms.archive.create", "badms.archive.view_self"),
        kind="student",
        dept="CSE",
    )
    upload = SimpleUploadedFile("notes.txt", b"notes", content_type="text/plain")
    resp = student.post(
        "/api/v1/badms/archive_requests",
        {
            "file_name": "notes.txt",
            "file_date": "2026-11-20",
            "owners": "Student X",
            "file_type": "text/plain",
            "reason": "Meeting notes",
            "initial_classification": "Routine",
            "attachment": upload,
        },
        format="multipart",
    )
    archive_id = resp.data["id"]

    hod = _client(
        stub_iam,
        user_id=205,
        permissions=("badms.archive.review_department",),
        kind="faculty",
        role="Department Head (HoD)",
        dept="CSE",
    )
    resp = hod.post(
        f"/api/v1/badms/archive_requests/{archive_id}/decision",
        {"decision": "reject", "note": "Not institutional record"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Rejected"


@override_settings(DEBUG=True)
def test_restoration_lifecycle(stub_iam):
    archive = ArchiveRequest.objects.create(
        user_id=102,
        department="CSE",
        requester_email="student2@example.test",
        file_name="thesis.pdf",
        file_date=date(2026, 10, 1),
        owners=["Student B"],
        file_type="application/pdf",
        reason="Research thesis",
        attachment_key="badms/incoming/102/thesis.pdf",
        archive_key="badms/incoming/102/thesis.pdf",
        attachment_size_bytes=2048,
        status="Sensitive Archive Encrypted",
        classification="Sensitive",
    )
    from modules.badms.services.storage import badms_storage
    badms_storage().save(archive.attachment_key, BytesIO(b"thesis content"))

    student = _client(
        stub_iam,
        user_id=102,
        permissions=("badms.restore.create", "badms.restore.view_self"),
        kind="student",
        dept="CSE",
    )
    resp = student.post(
        "/api/v1/badms/restoration_requests",
        {"archive_request_id": archive.pk},
        format="json",
    )
    assert resp.status_code == 201
    restore_id = resp.data["id"]

    resp = student.get("/api/v1/badms/restoration_requests")
    assert resp.status_code == 200

    sysadmin = _client(
        stub_iam,
        user_id=302,
        permissions=("badms.restore.approve", "badms.restore.execute", "badms.restore.view_self"),
        kind="staff",
        role="System Administrator (SysAdmin)",
        dept="IT",
    )
    resp = sysadmin.post(
        f"/api/v1/badms/restoration_requests/{restore_id}/decision",
        {"decision": "approve"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Approved for Restoration"

    resp = sysadmin.post(
        f"/api/v1/badms/restoration_requests/{restore_id}/execution",
        {},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Restored"

    resp = student.get(f"/api/v1/badms/restoration_requests/{restore_id}/download")
    assert resp.status_code == 200


@override_settings(DEBUG=True)
def test_restoration_rejection_flow(stub_iam):
    archive = ArchiveRequest.objects.create(
        user_id=106,
        department="CSE",
        requester_email="student6@example.test",
        file_name="thesis2.pdf",
        file_date=date(2026, 10, 1),
        owners=["Student Y"],
        file_type="application/pdf",
        reason="Research thesis 2",
        attachment_key="badms/incoming/106/thesis2.pdf",
        archive_key="badms/incoming/106/thesis2.pdf",
        attachment_size_bytes=1024,
        status="Sensitive Archive Encrypted",
        classification="Sensitive",
    )
    student = _client(
        stub_iam,
        user_id=106,
        permissions=("badms.restore.create", "badms.restore.view_self"),
        kind="student",
        dept="CSE",
    )
    resp = student.post(
        "/api/v1/badms/restoration_requests",
        {"archive_request_id": archive.pk},
        format="json",
    )
    restore_id = resp.data["id"]

    sysadmin = _client(
        stub_iam,
        user_id=306,
        permissions=("badms.restore.approve",),
        kind="staff",
        role="System Administrator (SysAdmin)",
        dept="IT",
    )
    resp = sysadmin.post(
        f"/api/v1/badms/restoration_requests/{restore_id}/decision",
        {"decision": "reject"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Rejected"


@override_settings(DEBUG=True, BADMS_USER_QUOTA_BYTES=1000, BADMS_AVAILABLE_STORAGE_BYTES=1000000000)
def test_storage_extension_lifecycle(stub_iam):
    ArchiveRequest.objects.create(
        user_id=103,
        department="CSE",
        requester_email="student3@example.test",
        file_name="heavy.bin",
        file_date=date(2026, 11, 1),
        owners=["Student C"],
        file_type="application/octet-stream",
        reason="Large dataset",
        attachment_key="badms/heavy.bin",
        attachment_size_bytes=2000,
        status="Submitted",
        classification="Routine",
    )
    student = _client(
        stub_iam,
        user_id=103,
        permissions=("badms.storage_extension.create", "badms.storage_extension.review_department"),
        kind="student",
        dept="CSE",
    )
    resp = student.post(
        "/api/v1/badms/storage_extension_requests",
        {"requested_bytes": 50000000, "justification": "AI dataset training"},
        format="json",
    )
    assert resp.status_code == 201
    req_id = resp.data["id"]

    resp = student.get("/api/v1/badms/storage_extension_requests")
    assert resp.status_code == 200

    hod = _client(
        stub_iam,
        user_id=203,
        permissions=("badms.storage_extension.review_department",),
        kind="faculty",
        role="Department Head (HoD)",
        dept="CSE",
    )
    resp = hod.post(
        f"/api/v1/badms/storage_extension_requests/{req_id}/decision",
        {"decision": "approve", "note": "Approved for thesis"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "Approved"

    student = _client(
        stub_iam,
        user_id=103,
        permissions=("badms.storage_extension.create", "badms.storage_extension.review_department"),
        kind="student",
        dept="CSE",
    )
    resp = student.get("/api/v1/badms/storage_thresholds/me")
    assert resp.status_code == 200


@override_settings(DEBUG=True)
def test_backup_runs_and_schedules(stub_iam, monkeypatch):
    monkeypatch.setattr("modules.badms.tasks.execute_backup.delay", lambda run_id: None)
    sysadmin = _client(
        stub_iam,
        user_id=303,
        permissions=(
            "badms.backup.run_manual",
            "badms.backup.view",
            "badms.schedule_local.manage",
            "badms.schedule_global.manage",
            "badms.audit.view",
        ),
        kind="staff",
        role="System Administrator (SysAdmin)",
        dept="IT",
    )
    resp = sysadmin.post(
        "/api/v1/badms/backup_runs",
        {"dataset": "fusionlab"},
        format="json",
    )
    assert resp.status_code == 202

    resp = sysadmin.get("/api/v1/badms/backup_runs")
    assert resp.status_code == 200

    resp = sysadmin.post(
        "/api/v1/badms/schedules",
        {
            "scope": "local",
            "dataset": "fusionlab",
            "frequency": "daily",
            "scheduled_time": "02:00:00",
            "timezone": "Asia/Kolkata",
            "classifications": ["Routine"],
            "enabled": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    sched_id = resp.data["id"]

    resp = sysadmin.get("/api/v1/badms/schedules")
    assert resp.status_code == 200

    resp = sysadmin.patch(
        f"/api/v1/badms/schedules/{sched_id}",
        {"enabled": False},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["enabled"] is False

    resp = sysadmin.get("/api/v1/badms/audit_events")
    assert resp.status_code == 200


@override_settings(DEBUG=True)
def test_perform_backup_success_and_failure(monkeypatch, tmp_path):
    run = BackupRun.objects.create(
        trigger="manual",
        status="running",
        dataset="fusionlab",
        started_at=timezone.now(),
    )

    def fake_subprocess_success(cmd, **kwargs):
        out_file = None
        for i, arg in enumerate(cmd):
            if arg == "--file":
                out_file = cmd[i + 1]
                break
        if out_file:
            with open(out_file, "wb") as f:
                f.write(b"dump payload bytes")
        return MagicMock(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_subprocess_success)
    monkeypatch.setattr("shutil.which", lambda prog: "/usr/bin/pg_dump")

    finished = backups.perform_backup(run.pk)
    assert finished.status == "success"
    assert finished.integrity_verified is True
    assert finished.checksum_sha256 != ""

    run2 = BackupRun.objects.create(
        trigger="manual",
        status="running",
        dataset="fusionlab",
        started_at=timezone.now(),
    )

    def fake_subprocess_fail(cmd, **kwargs):
        return MagicMock(returncode=1)

    monkeypatch.setattr("subprocess.run", fake_subprocess_fail)
    failed = backups.perform_backup(run2.pk)
    assert failed.status == "failure"
    assert failed.integrity_verified is False


def test_effective_schedules():
    BackupSchedule.objects.all().delete()
    s1 = BackupSchedule.objects.create(
        scope="local", dataset="db1", frequency="daily",
        scheduled_time=time(1, 0), timezone="UTC", enabled=True, updated_by=1,
    )
    s2 = BackupSchedule.objects.create(
        scope="global", dataset="db1", frequency="daily",
        scheduled_time=time(2, 0), timezone="UTC", enabled=True, updated_by=1,
    )
    s3 = BackupSchedule.objects.create(
        scope="global", dataset="db2", frequency="weekly",
        scheduled_time=time(3, 0), timezone="UTC", enabled=True, updated_by=1,
    )
    eff = backups.effective_schedules()
    assert s1 in eff
    assert s2 not in eff
    assert s3 in eff


@override_settings(DEBUG=True)
def test_special_archive_and_reports(stub_iam):
    superadmin = _client(
        stub_iam,
        user_id=901,
        permissions=("badms.archive.special",),
        kind="staff",
        role="Super Admin",
        dept="IT",
    )
    upload = SimpleUploadedFile("legacy_db.dump", b"SQL dump", content_type="application/octet-stream")
    resp = superadmin.post(
        "/api/v1/badms/special_archives",
        {
            "offline_request_reference": "OFF-2026-001",
            "research_description": "Historical 2020 student registry migration",
            "attachment": upload,
        },
        format="multipart",
    )
    assert resp.status_code == 201

    hod = _client(
        stub_iam,
        user_id=204,
        permissions=("badms.reports.department",),
        kind="faculty",
        role="Department Head (HoD)",
        dept="CSE",
    )
    resp = hod.get("/api/v1/badms/reports/department")
    assert resp.status_code == 200

    security = _client(
        stub_iam,
        user_id=404,
        permissions=("badms.security.audit", "badms.security_policy.manage"),
        kind="staff",
        role="IT Security Team",
        dept="IT",
    )
    resp = security.get("/api/v1/badms/reports/security")
    assert resp.status_code == 200

    resp = security.get("/api/v1/badms/security_policies")
    assert resp.status_code == 200

    resp = security.put(
        "/api/v1/badms/security_policies",
        {
            "retention_days": {
                "Critical": 3650,
                "Sensitive": 1825,
                "Routine": 730,
                "Archival": 365,
            }
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["retention_days"]["Critical"] == 3650
