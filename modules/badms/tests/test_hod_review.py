"""Tests for HoD Approval & SysAdmin Classification (Phase 4)."""
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
from modules.badms.services.storage import consume_quota
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


@pytest.fixture
def cse_student():
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


@pytest.fixture
def cse_archive_request(cse_student):
    consume_quota(1001, 1048576)  # 1 MB consumed
    return ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="Thesis_2026.pdf",
        document_date="2026-05-15",
        file_type="pdf",
        file_size_bytes=1048576,
        reason="Masters thesis submission",
        status=ArchiveStatus.SUBMITTED,
    )


def test_cse_hod_can_approve_cse_request(stub_iam, cse_hod, cse_archive_request):
    client = _client(
        stub_iam,
        user_id=3003,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/hod-decision/",
        {"decision": "approve", "comments": "Thesis verified by department."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == ArchiveStatus.HOD_APPROVED
    assert res.data["hod_user_id"] == 3003
    assert res.data["hod_comments"] == "Thesis verified by department."
    assert res.data["hod_decided_at"] is not None

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(
        target_id=str(cse_archive_request.pk), action="badms.archive.hod_approve"
    ).first()
    assert audit is not None
    assert audit.actor_user_id == 3003
    assert audit.outcome == "success"

    # Verify notifications: to student and to sysadmin role
    student_notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="archive_hod_approved"
    ).first()
    assert student_notif is not None

    sysadmin_notif = BadmsNotification.objects.filter(
        recipient_role="sysadmin", notification_type="classification_required"
    ).first()
    assert sysadmin_notif is not None


def test_cse_hod_can_reject_and_quota_is_released(
    stub_iam, cse_hod, cse_archive_request
):
    quota_before = UserStorageQuota.objects.get(user_id=1001)
    assert quota_before.used_bytes == 1048576

    client = _client(
        stub_iam,
        user_id=3003,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/hod-decision/",
        {"decision": "reject", "comments": "Incomplete advisor signatures."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == ArchiveStatus.REJECTED
    assert res.data["hod_comments"] == "Incomplete advisor signatures."

    # Verify quota released back to 0
    quota_after = UserStorageQuota.objects.get(user_id=1001)
    assert quota_after.used_bytes == 0

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(
        target_id=str(cse_archive_request.pk), action="badms.archive.hod_reject"
    ).first()
    assert audit is not None
    assert audit.outcome == "rejected"

    # Verify rejection notification
    notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="archive_rejected"
    ).first()
    assert notif is not None
    assert "Incomplete advisor signatures." in notif.message


def test_reject_requires_comments(stub_iam, cse_hod, cse_archive_request):
    client = _client(
        stub_iam,
        user_id=3003,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/hod-decision/",
        {"decision": "reject", "comments": ""},
        format="json",
    )
    assert res.status_code == 400
    assert "Comments are required" in res.data["detail"]


def test_cross_department_hod_cannot_review(stub_iam, ece_hod, cse_archive_request):
    client = _client(
        stub_iam,
        user_id=4004,
        kind="faculty",
        active_role="HOD",
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/hod-decision/",
        {"decision": "approve", "comments": "Cross dept"},
        format="json",
    )
    assert res.status_code == 403
    err_msg = res.data.get("error", {}).get("message", "") or res.data.get("detail", "")
    assert "authorized to review requests within your department" in err_msg

    # Verify request status unchanged
    cse_archive_request.refresh_from_db()
    assert cse_archive_request.status == ArchiveStatus.SUBMITTED


def test_sysadmin_can_classify_routine(stub_iam, cse_archive_request):
    # Set to hod_approved first
    cse_archive_request.status = ArchiveStatus.HOD_APPROVED
    cse_archive_request.save()

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.ARCHIVE_CLASSIFY,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/classify/",
        {"classification": "routine", "comments": "Routine departmental thesis."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == ArchiveStatus.POLICY_APPLIED
    assert res.data["authoritative_classification"] == ArchiveClassification.ROUTINE
    assert res.data["sysadmin_user_id"] == 99
    assert res.data["sysadmin_comments"] == "Routine departmental thesis."

    # Audit log check
    audit = BadmsAuditLog.objects.filter(
        target_id=str(cse_archive_request.pk), action="badms.archive.classify"
    ).first()
    assert audit is not None
    assert audit.details["classification"] == "routine"


def test_sysadmin_classify_sensitive_routes_to_security(stub_iam, cse_archive_request):
    # Set to hod_approved first
    cse_archive_request.status = ArchiveStatus.HOD_APPROVED
    cse_archive_request.save()

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.ARCHIVE_CLASSIFY,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/classify/",
        {"classification": "sensitive", "comments": "Contains proprietary lab data."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == ArchiveStatus.ROUTED_TO_SECURITY
    assert res.data["authoritative_classification"] == ArchiveClassification.SENSITIVE

    # Notification to IT Security
    security_notif = BadmsNotification.objects.filter(
        recipient_role="it_security", notification_type="security_encryption_required"
    ).first()
    assert security_notif is not None
    assert "AES-256" in security_notif.message


def test_cannot_classify_before_hod_approval(stub_iam, cse_archive_request):
    assert cse_archive_request.status == ArchiveStatus.SUBMITTED

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.ARCHIVE_CLASSIFY,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/classify/",
        {"classification": "routine"},
        format="json",
    )
    assert res.status_code == 400
    assert "must be 'hod_approved'" in res.data["detail"]


def test_unauthorized_user_cannot_classify(stub_iam, cse_archive_request):
    cse_archive_request.status = ArchiveStatus.HOD_APPROVED
    cse_archive_request.save()

    client = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF,),  # Missing p.ARCHIVE_CLASSIFY
    )

    res = client.post(
        f"/api/v1/badms/archives/{cse_archive_request.pk}/classify/",
        {"classification": "routine"},
        format="json",
    )
    assert res.status_code == 403
