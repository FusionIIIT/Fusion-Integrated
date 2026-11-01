"""Tests for BADMS Secure Archival Backend (Phase 3)."""
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
    UserStorageQuota,
)
from modules.badms.services.department import get_user_department
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


@pytest.fixture
def cse_user():
    return UserRef.objects.create(
        user_id=1001,
        username="u1001",
        display_name="Student CSE",
        kind="student",
        department="CSE",
        discipline="CSE",
        is_active=True,
    )


@pytest.fixture
def ece_user():
    return UserRef.objects.create(
        user_id=2002,
        username="u2002",
        display_name="Student ECE",
        kind="student",
        department="ECE",
        discipline="ECE",
        is_active=True,
    )


@pytest.fixture
def cse_hod():
    return UserRef.objects.create(
        user_id=3003,
        username="u3003",
        display_name="HoD CSE",
        kind="faculty",
        department="CSE",
        discipline="CSE",
        is_active=True,
    )


@pytest.fixture
def ece_hod():
    return UserRef.objects.create(
        user_id=4004,
        username="u4004",
        display_name="HoD ECE",
        kind="faculty",
        department="ECE",
        discipline="ECE",
        is_active=True,
    )


def test_user_can_submit_valid_archival_request(stub_iam, cse_user):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_CREATE, p.ARCHIVE_VIEW_SELF),
    )

    payload = {
        "file_name": "Project_Report_Final.pdf",
        "document_date": "2026-05-15",
        "file_type": "pdf",
        "file_size_bytes": 1048576,  # 1 MB
        "reason": "Final year capstone project archive submission.",
        "owners": ["u1001", "u1002"],
    }

    res = client.post("/api/v1/badms/archives/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["file_name"] == "Project_Report_Final.pdf"
    assert data["department"] == "CSE"
    assert data["status"] == ArchiveStatus.SUBMITTED
    assert data["initial_classification"] == ArchiveClassification.ROUTINE
    assert data["user_id"] == 1001
    assert data["file_size_bytes"] == 1048576

    # Verify quota consumed
    quota = UserStorageQuota.objects.get(user_id=1001)
    assert quota.used_bytes == 1048576

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(target_id=str(data["id"])).first()
    assert audit is not None
    assert audit.action == "badms.archive.submit"
    assert audit.actor_user_id == 1001
    assert audit.outcome == "success"

    # Verify notifications
    user_notif = BadmsNotification.objects.filter(user_id=1001).first()
    assert user_notif is not None
    assert "submitted" in user_notif.subject.lower()

    hod_notif = BadmsNotification.objects.filter(recipient_role="HOD").first()
    assert hod_notif is not None
    assert "CSE" in hod_notif.subject


def test_submission_fails_when_quota_exceeded(stub_iam, cse_user):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_CREATE, p.ARCHIVE_VIEW_SELF),
    )

    # User quota is 1GB by default. Request 2GB.
    excessive_bytes = 2 * 1024 * 1024 * 1024
    payload = {
        "file_name": "Huge_Dataset.tar.gz",
        "document_date": "2026-05-15",
        "file_type": "tar.gz",
        "file_size_bytes": excessive_bytes,
        "reason": "Dataset archive exceeding quota.",
    }

    res = client.post("/api/v1/badms/archives/", payload, format="json")
    assert res.status_code == 400
    assert res.data["code"] == "quota_exceeded"

    # No archival request should be created
    assert ArchivalRequest.objects.count() == 0


def test_submission_validation_errors(stub_iam, cse_user):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_CREATE, p.ARCHIVE_VIEW_SELF),
    )

    # Missing file_name
    res = client.post(
        "/api/v1/badms/archives/",
        {"document_date": "2026-05-15", "file_type": "pdf", "reason": "Test"},
        format="json",
    )
    assert res.status_code == 400

    # Negative file size
    res = client.post(
        "/api/v1/badms/archives/",
        {
            "file_name": "file.pdf",
            "document_date": "2026-05-15",
            "file_type": "pdf",
            "file_size_bytes": -50,
            "reason": "Test",
        },
        format="json",
    )
    assert res.status_code == 400


def test_permission_denied_without_create_grant(stub_iam, cse_user):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF,),  # Missing p.ARCHIVE_CREATE
    )

    payload = {
        "file_name": "Report.pdf",
        "document_date": "2026-05-15",
        "file_type": "pdf",
        "reason": "No create permission",
    }
    res = client.post("/api/v1/badms/archives/", payload, format="json")
    assert res.status_code == 403


def test_archive_scoping_for_user_hod_and_sysadmin(
    stub_iam, cse_user, ece_user, cse_hod, ece_hod
):
    # Setup two requests: one in CSE, one in ECE
    req_cse = ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="CSE_Doc.pdf",
        document_date="2026-05-10",
        file_type="pdf",
        file_size_bytes=1000,
        reason="CSE Research",
        status=ArchiveStatus.SUBMITTED,
    )
    req_ece = ArchivalRequest.objects.create(
        user_id=2002,
        department="ECE",
        file_name="ECE_Doc.pdf",
        document_date="2026-05-10",
        file_type="pdf",
        file_size_bytes=2000,
        reason="ECE Research",
        status=ArchiveStatus.SUBMITTED,
    )

    # 1. Student CSE sees ONLY their own request
    c_student = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF,),
    )
    res = c_student.get("/api/v1/badms/archives/")
    assert res.status_code == 200
    ids = [r["id"] for r in res.data["results"]]
    assert ids == [req_cse.pk]

    # Student CSE detail endpoint
    assert c_student.get(f"/api/v1/badms/archives/{req_cse.pk}/").status_code == 200
    assert c_student.get(f"/api/v1/badms/archives/{req_ece.pk}/").status_code == 404

    # 2. HoD CSE sees ONLY CSE request, NOT ECE
    c_cse_hod = _client(
        stub_iam,
        user_id=3003,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )
    res = c_cse_hod.get("/api/v1/badms/archives/")
    assert res.status_code == 200
    ids = [r["id"] for r in res.data["results"]]
    assert ids == [req_cse.pk]

    # HoD CSE detail endpoint
    assert c_cse_hod.get(f"/api/v1/badms/archives/{req_cse.pk}/").status_code == 200
    assert c_cse_hod.get(f"/api/v1/badms/archives/{req_ece.pk}/").status_code == 404

    # 3. HoD ECE sees ONLY ECE request, NOT CSE
    c_ece_hod = _client(
        stub_iam,
        user_id=4004,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )
    res = c_ece_hod.get("/api/v1/badms/archives/")
    assert res.status_code == 200
    ids = [r["id"] for r in res.data["results"]]
    assert ids == [req_ece.pk]

    # 4. SysAdmin sees ALL requests across all departments
    c_sysadmin = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW, p.ARCHIVE_CLASSIFY),
    )
    res = c_sysadmin.get("/api/v1/badms/archives/")
    assert res.status_code == 200
    ids = {r["id"] for r in res.data["results"]}
    assert ids == {req_cse.pk, req_ece.pk}
    assert c_sysadmin.get(f"/api/v1/badms/archives/{req_cse.pk}/").status_code == 200
    assert c_sysadmin.get(f"/api/v1/badms/archives/{req_ece.pk}/").status_code == 200


def test_quota_endpoint(stub_iam, cse_user):
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF,),
    )
    res = client.get("/api/v1/badms/quota/")
    assert res.status_code == 200
    assert res.data["user_id"] == 1001
    assert res.data["allocated_bytes"] == 1024 * 1024 * 1024
    assert res.data["used_bytes"] == 0
    assert res.data["remaining_bytes"] == 1024 * 1024 * 1024


def test_notifications_endpoint(stub_iam, cse_user):
    BadmsNotification.objects.create(
        user_id=1001,
        subject="Test Notification",
        message="Your test notification message.",
        notification_type="test",
    )
    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF,),
    )
    res = client.get("/api/v1/badms/notifications/")
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["subject"] == "Test Notification"
