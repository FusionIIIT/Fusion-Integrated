"""Tests for BADMS Storage Extension Workflow (Phase 10)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    BadmsAuditLog,
    BadmsNotification,
    StorageExtensionRequest,
    StorageExtensionStatus,
    UserStorageQuota,
)
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
        user_id=2001,
        username="u2001",
        display_name="CSE Student",
        kind="student",
        department="CSE",
        is_active=True,
    )


@pytest.fixture
def cse_hod():
    return UserRef.objects.create(
        user_id=2002,
        username="u2002",
        display_name="CSE HoD",
        kind="faculty",
        department="CSE",
        is_active=True,
    )


@pytest.fixture
def ee_hod():
    return UserRef.objects.create(
        user_id=2003,
        username="u2003",
        display_name="EE HoD",
        kind="faculty",
        department="EE",
        is_active=True,
    )


@pytest.fixture
def sysadmin_user():
    return UserRef.objects.create(
        user_id=2004,
        username="u2004",
        display_name="System Admin",
        kind="staff",
        department="IT",
        is_active=True,
    )


def test_user_can_submit_storage_extension(stub_iam, cse_student):
    client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )

    payload = {
        "requested_bytes": 536870912,  # 512 MB
        "reason": "Need additional capacity for senior thesis deep learning datasets.",
    }
    res = client.post("/api/v1/badms/storage-extensions/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["user_id"] == 2001
    assert data["department"] == "CSE"
    assert data["requested_bytes"] == 536870912
    assert data["status"] == StorageExtensionStatus.SUBMITTED

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(target_id=str(data["id"])).first()
    assert audit is not None
    assert audit.action == "badms.storage.submit"

    # Verify notifications
    notifs = BadmsNotification.objects.filter(related_object_id=str(data["id"]))
    assert notifs.count() >= 2


def test_hod_approves_storage_extension_increases_quota(stub_iam, cse_student, cse_hod):
    student_client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )

    # Student submits
    res = student_client.post(
        "/api/v1/badms/storage-extensions/",
        {
            "requested_bytes": 1073741824,  # +1 GB
            "reason": "Extensive research archive storage required.",
        },
        format="json",
    )
    assert res.status_code == 201
    ext_id = res.data["id"]

    # Initial quota is 1GB
    quota = UserStorageQuota.objects.get(user_id=2001)
    initial_allocated = quota.allocated_bytes

    # CSE HoD reviews and approves
    hod_client = _client(
        stub_iam,
        user_id=2002,
        kind="faculty",
        modules=("badms",),
        permissions=(p.STORAGE_REVIEW, p.STORAGE_VIEW),
        active_role="HOD",
    )

    review_res = hod_client.post(
        f"/api/v1/badms/storage-extensions/{ext_id}/decision/",
        {"decision": "approve", "comments": "Approved for thesis project work."},
        format="json",
    )
    assert review_res.status_code == 200, review_res.data
    assert review_res.data["status"] == StorageExtensionStatus.HOD_APPROVED
    assert review_res.data["hod_user_id"] == 2002

    # Quota must be increased
    quota.refresh_from_db()
    assert quota.allocated_bytes == initial_allocated + 1073741824


def test_hod_rejects_storage_extension_preserves_quota(stub_iam, cse_student, cse_hod):
    student_client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )

    res = student_client.post(
        "/api/v1/badms/storage-extensions/",
        {
            "requested_bytes": 5368709120,  # 5 GB
            "reason": "Uncompressed raw video storage.",
        },
        format="json",
    )
    assert res.status_code == 201
    ext_id = res.data["id"]

    quota = UserStorageQuota.objects.get(user_id=2001)
    initial_allocated = quota.allocated_bytes

    hod_client = _client(
        stub_iam,
        user_id=2002,
        kind="faculty",
        modules=("badms",),
        permissions=(p.STORAGE_REVIEW, p.STORAGE_VIEW),
        active_role="HOD",
    )

    review_res = hod_client.post(
        f"/api/v1/badms/storage-extensions/{ext_id}/decision/",
        {
            "decision": "reject",
            "comments": "Video storage exceeds departmental undergraduate allowance.",
        },
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.data["status"] == StorageExtensionStatus.REJECTED

    # Quota remains unchanged
    quota.refresh_from_db()
    assert quota.allocated_bytes == initial_allocated


def test_rejection_without_comments_rejected(stub_iam, cse_student, cse_hod):
    student_client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )
    res = student_client.post(
        "/api/v1/badms/storage-extensions/",
        {"requested_bytes": 104857600, "reason": "Test quota reason"},
        format="json",
    )
    ext_id = res.data["id"]

    hod_client = _client(
        stub_iam,
        user_id=2002,
        kind="faculty",
        modules=("badms",),
        permissions=(p.STORAGE_REVIEW, p.STORAGE_VIEW),
        active_role="HOD",
    )
    bad_res = hod_client.post(
        f"/api/v1/badms/storage-extensions/{ext_id}/decision/",
        {"decision": "reject", "comments": "   "},
        format="json",
    )
    assert bad_res.status_code == 400


def test_cross_department_hod_blocked(stub_iam, cse_student, ee_hod):
    student_client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )
    res = student_client.post(
        "/api/v1/badms/storage-extensions/",
        {"requested_bytes": 104857600, "reason": "CSE Thesis data"},
        format="json",
    )
    ext_id = res.data["id"]

    # EE HoD attempts to approve CSE request -> Forbidden
    ee_client = _client(
        stub_iam,
        user_id=2003,
        kind="faculty",
        modules=("badms",),
        permissions=(p.STORAGE_REVIEW, p.STORAGE_VIEW),
        active_role="HOD",
    )
    block_res = ee_client.post(
        f"/api/v1/badms/storage-extensions/{ext_id}/decision/",
        {"decision": "approve", "comments": "Approved"},
        format="json",
    )
    assert block_res.status_code == 403


def test_storage_extension_list_scoping(stub_iam, cse_student, cse_hod, sysadmin_user):
    # Student submits
    student_client = _client(
        stub_iam,
        user_id=2001,
        kind="student",
        modules=("badms",),
        permissions=(p.STORAGE_CREATE, p.STORAGE_VIEW_SELF),
    )
    student_client.post(
        "/api/v1/badms/storage-extensions/",
        {"requested_bytes": 209715200, "reason": "Self project"},
        format="json",
    )

    # Student list
    list_student = student_client.get("/api/v1/badms/storage-extensions/")
    assert list_student.status_code == 200
    assert list_student.data["count"] >= 1

    # CSE HoD list
    hod_client = _client(
        stub_iam,
        user_id=2002,
        kind="faculty",
        modules=("badms",),
        permissions=(p.STORAGE_REVIEW,),
        active_role="HOD",
    )
    list_hod = hod_client.get("/api/v1/badms/storage-extensions/")
    assert list_hod.status_code == 200
    assert all(r["department"] == "CSE" for r in list_hod.data["results"])

    # Sysadmin list
    sys_client = _client(
        stub_iam,
        user_id=2004,
        kind="staff",
        modules=("badms",),
        permissions=(p.STORAGE_VIEW,),
        active_role="sysadmin",
    )
    list_sys = sys_client.get("/api/v1/badms/storage-extensions/")
    assert list_sys.status_code == 200
    assert list_sys.data["count"] >= 1
