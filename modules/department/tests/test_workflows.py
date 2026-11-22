import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.department.models import Announcement, Feedback, Notice, StockItem, StockMovement
from modules.department.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


@pytest.fixture
def role_client(stub_iam):
    def as_role(role, user_id=10, department="CSE", kind="faculty"):
        identity = UserRef(user_id, f"u{user_id}", "Test user", kind, department=department)
        stub_iam(session=make_session(user_id=user_id, roles=[role], active_role=role, kind=kind,
                                      modules=["department"], permissions=ROLE_GRANTS[role]),
                 users={user_id: identity})
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-session")
        return client
    return as_role


def post(client, path, data):
    return client.post(f"{BASE}/{path}", data, format="json")


def test_announcement_publish_notice_and_hod_hide(role_client):
    """UC-DEPT-002/003; BR-DEPT-001/003/004; AFR-DEPT-046."""
    faculty = role_client("faculty")
    publication = {"content": "Department seminar", "target_roles": ["student"],
                   "target_programmes": [], "target_batch_years": []}
    published = post(faculty, "announcements", publication)
    assert published.status_code == 201
    pk = published.json()["id"]
    assert not faculty.get(f"{BASE}/notices").json()["results"]

    student = role_client("student", user_id=12, kind="student")
    assert len(student.get(f"{BASE}/notices").json()["results"]) == 1
    hod = role_client("HOD (CSE)", user_id=13)
    assert [row["id"] for row in hod.get(f"{BASE}/announcements/managed").json()["results"]] == [pk]
    assert post(hod, f"announcements/{pk}/action", {"action": "hide"}).status_code == 204
    assert not Announcement.objects.get(pk=pk).is_active


def test_stock_approval_issue_and_rejection(role_client):
    """UC-DEPT-004/005/006/019; BW-DEPT-01/02; AFR-DEPT-009-016 and 041-043."""
    admin = role_client("deptadmin_cse", kind="staff")
    item = post(admin, "inventory", {"name": "Cable", "quantity": 4})
    assert item.status_code == 201
    item_id = item.json()["id"]
    faculty = role_client("faculty", user_id=11)
    accepted = post(faculty, "stock-requests", {"item_id": item_id, "quantity": 3})
    rejected = post(faculty, "stock-requests", {"item_id": item_id, "quantity": 3})
    assert accepted.status_code == rejected.status_code == 201
    assert StockItem.objects.get(pk=item_id).quantity == 4
    approved_id, rejected_id = accepted.json()["id"], rejected.json()["id"]

    hod = role_client("HOD (CSE)", user_id=12)
    assert post(hod, f"stock-requests/{approved_id}/action", {"action": "approve"}).status_code == 200
    assert post(hod, f"stock-requests/{rejected_id}/action", {"action": "reject"}).status_code == 200
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, f"stock-requests/{approved_id}/action", {"action": "issue"}).status_code == 200
    assert StockItem.objects.get(pk=item_id).quantity == 1
    assert list(StockMovement.objects.order_by("id").values_list("delta", flat=True)) == [4, -3]

    faculty = role_client("faculty", user_id=11)
    assert [r["id"] for r in faculty.get(f"{BASE}/stock-requests").json()["results"]] == [approved_id]
    assert Notice.objects.filter(user_id=11).count() == 2


def test_stock_audit_cannot_be_updated(role_client):
    """BR-DEPT-016 append-only movement history."""
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, "inventory", {"name": "Adapter", "quantity": 2}).status_code == 201
    with pytest.raises(IntegrityError), transaction.atomic():
        StockMovement.objects.update(delta=1)
    assert StockMovement.objects.get().delta == 2


def test_feedback_is_reviewed_before_hod_disposition(role_client):
    """UC-DEPT-007/008/014; BR-DEPT-017/018; BW-DEPT-04."""
    student = role_client("student", user_id=20, kind="student")
    submission = post(student, "feedback", {"content": "Add a ramp to the laboratory"})
    assert submission.status_code == 201
    pk = submission.json()["id"]
    assert set(submission.json()) == {"id", "status"}
    hod = role_client("HOD (CSE)", user_id=21)
    assert hod.get(f"{BASE}/feedback").json()["results"] == []
    admin = role_client("deptadmin_cse", kind="staff", user_id=22)
    assert post(admin, f"feedback/{pk}/action", {"action": "review", "category": "Access"}).status_code == 200
    hod = role_client("HOD (CSE)", user_id=21)
    assert post(hod, f"feedback/{pk}/action", {"action": "resolve"}).status_code == 200
    row = Feedback.objects.get(pk=pk)
    assert row.status == Feedback.Status.RESOLVED
    assert row.reviewed_by_id == 22
    assert row.disposed_by_id == 21
    assert Notice.objects.filter(user_id=20).exists()
