import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef as IamUserRef
from modules.badms.models import ArchivalRequest

pytestmark = pytest.mark.django_db

SUBMIT = "badms.archival.submit"
REVIEW = "badms.archival.review"
FILE_LINK = "https://drive.google.com/file/d/abcdefghijk/view"


def _client(stub_iam, *, user_id=1001, department="Engineering",
            permissions=(SUBMIT,), kind="student"):
    user = IamUserRef(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"User {user_id}",
        kind=kind,
        department=department,
    )
    stub_iam(
        make_session(user_id=user_id, modules=("badms",),
                     permissions=permissions, kind=kind),
        users={user_id: user},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _request(**overrides):
    return {
        "file_name": "research-data.csv",
        "file_date": "2026-10-25",
        "owners": ["Ada Lovelace"],
        "file_type": "Dataset",
        "reason": "Preserve the research results.",
        "attachment_url": FILE_LINK,
        **overrides,
    }


def test_submission_uses_directory_department_and_default_classification(stub_iam):
    client = _client(stub_iam)

    response = client.post("/api/v1/badms/archival-requests", _request(),
                           format="json")

    assert response.status_code == 201
    assert response.json()["department"] == "Engineering"
    assert response.json()["status"] == "submitted"
    assert response.json()["initial_classification"] == "routine"
    assert response.json()["attachment_url"] == FILE_LINK
    assert ArchivalRequest.objects.count() == 1


def test_submission_rejects_non_drive_links_without_creating_a_request(stub_iam):
    client = _client(stub_iam)

    response = client.post(
        "/api/v1/badms/archival-requests",
        _request(attachment_url="https://example.com/file"),
        format="json",
    )

    assert response.status_code == 400
    assert ArchivalRequest.objects.count() == 0


def test_requesters_only_see_their_own_requests(stub_iam):
    own = ArchivalRequest.objects.create(
        requester_user_id=1001, department="Engineering", **_request())
    ArchivalRequest.objects.create(
        requester_user_id=1002, department="Engineering", **_request())
    client = _client(stub_iam)

    response = client.get("/api/v1/badms/archival-requests")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [own.id]


def test_hod_can_decide_only_requests_from_their_department(stub_iam):
    in_department = ArchivalRequest.objects.create(
        requester_user_id=1001, department="Engineering", **_request())
    outside_department = ArchivalRequest.objects.create(
        requester_user_id=1002, department="Physics", **_request())
    client = _client(stub_iam, user_id=9000, department="Engineering",
                     permissions=(SUBMIT, REVIEW), kind="staff")

    visible = client.get("/api/v1/badms/archival-requests")
    response = client.post(
        f"/api/v1/badms/archival-requests/{in_department.id}/decision",
        {"decision": "approve"},
        format="json",
    )
    denied = client.post(
        f"/api/v1/badms/archival-requests/{outside_department.id}/decision",
        {"decision": "reject"},
        format="json",
    )

    assert [row["id"] for row in visible.json()] == [in_department.id]
    assert response.status_code == 200
    assert response.json()["status"] == "hod_approved"
    assert response.json()["decided_by_user_id"] == 9000
    assert denied.status_code == 404


def test_non_hod_cannot_decide_a_request(stub_iam):
    archival_request = ArchivalRequest.objects.create(
        requester_user_id=1001, department="Engineering", **_request())
    client = _client(stub_iam)

    response = client.post(
        f"/api/v1/badms/archival-requests/{archival_request.id}/decision",
        {"decision": "approve"},
        format="json",
    )

    assert response.status_code == 403
