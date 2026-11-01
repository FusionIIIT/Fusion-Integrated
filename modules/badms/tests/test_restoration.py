"""Tests for BADMS Restoration Workflow (Phase 9)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
    BadmsAuditLog,
    BadmsNotification,
    RestorationRequest,
    RestorationStatus,
)
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


@pytest.fixture
def student_user():
    return UserRef.objects.create(
        user_id=1001,
        username="u1001",
        display_name="Student",
        kind="student",
        department="CSE",
        is_active=True,
    )


@pytest.fixture
def routine_archive(student_user):
    return ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="LectureNotes.pdf",
        document_date="2026-05-01",
        file_type="pdf",
        file_size_bytes=10000,
        reason="Course material",
        initial_classification=ArchiveClassification.ROUTINE,
        authoritative_classification=ArchiveClassification.ROUTINE,
        status=ArchiveStatus.POLICY_APPLIED,
    )


@pytest.fixture
def sensitive_archive(student_user):
    return ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="MedicalSensorData.dat",
        document_date="2026-05-01",
        file_type="dat",
        file_size_bytes=20000,
        reason="Clinical trial sensors",
        initial_classification=ArchiveClassification.ROUTINE,
        authoritative_classification=ArchiveClassification.SENSITIVE,
        is_encrypted=True,
        encryption_algorithm="AES-256-GCM",
        status=ArchiveStatus.ENCRYPTED_ARCHIVE_CREATED,
    )


def test_non_sensitive_archive_restores_immediately(stub_iam, routine_archive):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.RESTORATION_CREATE, p.RESTORATION_VIEW_SELF),
    )

    payload = {
        "archive_id": routine_archive.pk,
        "reason": "Need course notes for upcoming examination.",
        "target_destination": "/home/student/restored",
    }
    res = client.post("/api/v1/badms/restorations/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["status"] == RestorationStatus.COMPLETED
    assert data["is_sensitive"] is False
    assert data["integrity_verified"] is True
    assert data["restored_at"] is not None

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(target_id=str(data["id"])).first()
    assert audit is not None
    assert audit.action == "badms.restoration.execute_standard"

    # Verify notification
    notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="restoration_completed"
    ).first()
    assert notif is not None
    assert "Completed" in notif.subject


def test_sensitive_archive_requires_sysadmin_approval(stub_iam, sensitive_archive):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.RESTORATION_CREATE, p.RESTORATION_VIEW_SELF),
    )

    payload = {
        "archive_id": sensitive_archive.pk,
        "reason": "Clinical audit re-analysis.",
        "target_destination": "/secure/clinical_data",
    }
    res = client.post("/api/v1/badms/restorations/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["status"] == RestorationStatus.PENDING_APPROVAL
    assert data["is_sensitive"] is True
    assert data["integrity_verified"] is False
    assert data["restored_at"] is None

    # Check alert to SysAdmin
    sysadmin_notif = BadmsNotification.objects.filter(
        recipient_role="sysadmin", notification_type="restoration_approval_required"
    ).first()
    assert sysadmin_notif is not None
    assert "Approval Required" in sysadmin_notif.subject


def test_sysadmin_approves_sensitive_restoration(stub_iam, sensitive_archive):
    # Setup pending restoration
    restoration = RestorationRequest.objects.create(
        archive_id=sensitive_archive.pk,
        requester_user_id=1001,
        target_name=sensitive_archive.file_name,
        reason="Research evaluation",
        is_sensitive=True,
        status=RestorationStatus.PENDING_APPROVAL,
    )

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.RESTORATION_APPROVE, p.RESTORATION_VIEW),
    )

    res = client.post(
        f"/api/v1/badms/restorations/{restoration.pk}/decision/",
        {"decision": "approve", "comments": "Approved after security clearance verification."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == RestorationStatus.COMPLETED
    assert res.data["approved_by_user_id"] == 99
    assert res.data["integrity_verified"] is True
    assert res.data["restored_at"] is not None

    # Verify requester notification
    notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="restoration_completed"
    ).first()
    assert notif is not None
    assert "Approved & Restored" in notif.subject


def test_sysadmin_rejects_sensitive_restoration(stub_iam, sensitive_archive):
    restoration = RestorationRequest.objects.create(
        archive_id=sensitive_archive.pk,
        requester_user_id=1001,
        target_name=sensitive_archive.file_name,
        reason="Unauthorized retrieval",
        is_sensitive=True,
        status=RestorationStatus.PENDING_APPROVAL,
    )

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.RESTORATION_APPROVE, p.RESTORATION_VIEW),
    )

    res = client.post(
        f"/api/v1/badms/restorations/{restoration.pk}/decision/",
        {"decision": "reject", "comments": "Policy violation: export restriction."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == RestorationStatus.REJECTED
    assert res.data["error_message"] == "Policy violation: export restriction."

    # Notification check
    notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="restoration_rejected"
    ).first()
    assert notif is not None
    assert "Rejected" in notif.subject


def test_unauthorized_user_cannot_approve(stub_iam, sensitive_archive):
    restoration = RestorationRequest.objects.create(
        archive_id=sensitive_archive.pk,
        requester_user_id=1001,
        target_name=sensitive_archive.file_name,
        reason="Research",
        is_sensitive=True,
        status=RestorationStatus.PENDING_APPROVAL,
    )

    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.RESTORATION_CREATE,),  # Missing p.RESTORATION_APPROVE
    )

    res = client.post(
        f"/api/v1/badms/restorations/{restoration.pk}/decision/",
        {"decision": "approve"},
        format="json",
    )
    assert res.status_code == 403


def test_restoration_scoping(stub_iam, routine_archive, sensitive_archive):
    r1 = RestorationRequest.objects.create(
        archive_id=routine_archive.pk,
        requester_user_id=1001,
        target_name="User1001_Doc",
        reason="Test",
        status=RestorationStatus.COMPLETED,
    )
    r2 = RestorationRequest.objects.create(
        archive_id=sensitive_archive.pk,
        requester_user_id=2002,
        target_name="User2002_Doc",
        reason="Test",
        status=RestorationStatus.COMPLETED,
    )

    # Student 1001 sees only r1
    c_student = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.RESTORATION_VIEW_SELF,),
    )
    res = c_student.get("/api/v1/badms/restorations/")
    assert res.status_code == 200
    ids = [r["id"] for r in res.data["results"]]
    assert ids == [r1.pk]

    # SysAdmin sees both
    c_sysadmin = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.RESTORATION_VIEW,),
    )
    res_admin = c_sysadmin.get("/api/v1/badms/restorations/")
    assert res_admin.status_code == 200
    ids_admin = {r["id"] for r in res_admin.data["results"]}
    assert {r1.pk, r2.pk}.issubset(ids_admin)
