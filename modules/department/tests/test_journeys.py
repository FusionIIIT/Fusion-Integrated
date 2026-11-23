import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.department.models import (
    Announcement,
    Feedback,
    Notice,
    StockItem,
    StockMovement,
    StockRequest,
    TimetableSlot,
)
from modules.department.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


@pytest.fixture
def role_client(stub_iam):
    def as_role(role, user_id=10, department="CSE", kind="faculty", **attributes):
        identity = UserRef(user_id, f"u{user_id}", "Test user", kind,
                           department=department, **attributes)
        stub_iam(session=make_session(user_id=user_id, roles=[role], active_role=role, kind=kind,
                                      modules=["department"], permissions=ROLE_GRANTS[role]),
                 users={11: UserRef(11, "faculty", "Instructor", "faculty", department="CSE"),
                        user_id: identity})
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-session")
        return client
    return as_role


def post(client, path, data):
    return client.post(f"{BASE}/{path}", data, format="json")


def test_announcement_publish_notice_and_hod_hide(role_client):
    """UC-DEPT-002, UC-DEPT-003; BR-DEPT-001, BR-DEPT-003, BR-DEPT-004; AFR-DEPT-046."""
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
    """UC-DEPT-004, UC-DEPT-005, UC-DEPT-006, UC-DEPT-019; BW-DEPT-01, BW-DEPT-02; AFR-DEPT-009-016 and 041-043."""
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
    assert Notice.objects.filter(audience="admin", department="CSE").count() == 2
    assert Notice.objects.filter(audience="hod", department="CSE").count() == 2

    hod = role_client("HOD (CSE)", user_id=12)
    assert post(hod, f"stock-requests/{approved_id}/action", {"action": "approve"}).status_code == 200
    assert post(hod, f"stock-requests/{rejected_id}/action", {"action": "reject"}).status_code == 200
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, f"stock-requests/{approved_id}/action", {"action": "issue"}).status_code == 200
    for decision in StockRequest.objects.filter(pk__in=[approved_id, rejected_id]):
        assert decision.decided_by_id == 12 and decision.decided_at is not None
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
    """UC-DEPT-007, UC-DEPT-008, UC-DEPT-014; BR-DEPT-017, BR-DEPT-018; BW-DEPT-04."""
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


def test_timetable_batches_are_atomic_and_student_reads_match_cohort(role_client):
    """UC-DEPT-009, UC-DEPT-018; BR-DEPT-010; AFR-DEPT-029-031/036/037."""
    admin = role_client("deptadmin_cse", kind="staff")
    slot = {"title": "Programming", "kind": "class", "term": "2026 autumn", "day": 0,
            "starts_at": "10:00", "ends_at": "11:00", "room": "R1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024}
    overlapping = {**slot, "title": "Networks", "starts_at": "10:30", "ends_at": "11:30"}
    assert post(admin, "timetable", {"slots": [slot, overlapping]}).status_code == 409
    assert not TimetableSlot.objects.exists()

    next_slot = {**slot, "title": "Networks", "starts_at": "11:00", "ends_at": "12:00",
                 "batch_year": 2025}
    response = post(admin, "timetable", {"slots": [slot, next_slot]})
    assert response.status_code == 201
    first_id = response.json()[0]["id"]
    edit = admin.put(f"{BASE}/timetable/{first_id}", {**slot, "title": "Data structures"}, format="json")
    assert edit.status_code == 200
    student = role_client("student", user_id=12, kind="student", programme="BTech", batch_year=2024)
    assert student.get(f"{BASE}/academic-context").json() == {"programme": "BTech", "batch_year": 2024}
    assert [row["title"] for row in student.get(f"{BASE}/timetable").json()["results"]] == ["Data structures"]


def test_faculty_lab_resources_use_department_scope(role_client):
    """UC-DEPT-011, UC-DEPT-017; BR-DEPT-012; AFR-DEPT-034/035."""
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, "labs", {"name": "Networks", "details": "Ten workstations"}).status_code == 200
    assert post(admin, "labs", {"name": "Networks", "details": "Twelve workstations"}).status_code == 200
    faculty = role_client("faculty")
    assert [row["details"] for row in faculty.get(f"{BASE}/labs").json()["results"]] == ["Twelve workstations"]
    other = role_client("faculty", department="Design")
    assert other.get(f"{BASE}/labs").json()["results"] == []


def test_department_general_save_and_official_decision(role_client):
    """UC-DEPT-010, UC-DEPT-012; BR-DEPT-011, BR-DEPT-013; BW-DEPT-05, BW-DEPT-06; AFR-DEPT-038-040."""
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, "details", {"general_information": "Office hours 9 to 5"}).status_code == 200
    accepted = post(admin, "proposals", {"field": "official_name", "value": "Computer Science"})
    rejected = post(admin, "proposals", {"field": "core_policies", "value": "Proposed policy"})
    assert accepted.status_code == rejected.status_code == 201
    assert admin.get(f"{BASE}/details").json()["official_name"] == ""
    hod = role_client("HOD (CSE)", user_id=11)
    path = f"proposals/{accepted.json()['id']}/action"
    assert post(hod, path, {"action": "approve"}).status_code == 200
    path = f"proposals/{rejected.json()['id']}/action"
    assert post(hod, path, {"action": "reject"}).status_code == 200
    assert hod.get(f"{BASE}/details").json() == {
        "department": "CSE", "official_name": "Computer Science", "core_policies": "",
        "general_information": "Office hours 9 to 5",
    }


def test_stock_shortage_after_approval_preserves_existing_movements(role_client):
    """BR-DEPT-007, BR-DEPT-015, BR-DEPT-016 and the approved concurrent-shortage interpretation."""
    admin = role_client("deptadmin_cse", kind="staff")
    item = post(admin, "inventory", {"name": "Scope probe", "quantity": 4}).json()["id"]
    assert post(admin, "inventory", {"name": "Scope probe", "quantity": 1}).json()["quantity"] == 5
    faculty = role_client("faculty")
    assert post(faculty, "stock-requests", {"item_id": item, "quantity": 6}).status_code == 409
    ids = [post(faculty, "stock-requests", {"item_id": item, "quantity": 4}).json()["id"]
           for _ in range(2)]
    admin = role_client("deptadmin_cse", kind="staff")
    assert post(admin, f"stock-requests/{ids[0]}/action", {"action": "issue"}).status_code == 409
    hod = role_client("HOD (CSE)")
    assert len(hod.get(f"{BASE}/stock-requests").json()["results"]) == 2
    for request_id in ids:
        assert post(hod, f"stock-requests/{request_id}/action", {"action": "approve"}).status_code == 200
    admin = role_client("deptadmin_cse", kind="staff")
    assert len(admin.get(f"{BASE}/stock-requests").json()["results"]) == 2
    assert len(admin.get(f"{BASE}/notices").json()["results"]) == 2
    assert post(admin, f"stock-requests/{ids[0]}/action", {"action": "issue"}).status_code == 200
    assert post(admin, f"stock-requests/{ids[1]}/action", {"action": "issue"}).status_code == 409
    assert StockItem.objects.get(pk=item).quantity == 1
    assert StockMovement.objects.filter(delta__lt=0).count() == 1
    assert admin.get(f"{BASE}/stock-requests").json()["results"][0]["id"] == ids[1]


def test_announcement_edit_and_delete_are_department_hod_actions(role_client):
    """UC-DEPT-003; BR-DEPT-003, BR-DEPT-004; AFR-DEPT-004/006."""
    author = role_client("faculty")
    payload = {"content": "Notice", "target_roles": [],
               "target_programmes": [], "target_batch_years": []}
    pk = post(author, "announcements", payload).json()["id"]
    url = f"announcements/{pk}/action"
    other_hod = role_client("HOD (Design)", department="Design")
    assert post(other_hod, url, {"action": "hide"}).status_code == 404
    hod = role_client("HOD (CSE)")
    assert post(hod, url, {"action": "edit"}).status_code == 400
    assert post(hod, url, {"action": "edit", "announcement": {**payload, "content": "Revised"}}).status_code == 204
    assert Announcement.objects.get(pk=pk).content == "Revised"
    assert post(hod, url, {"action": "delete"}).status_code == 204
    assert not Announcement.objects.filter(pk=pk).exists()
    assert not Notice.objects.exists()


def test_simple_feedback_records_initial_review_before_closing(role_client):
    """UC-DEPT-008; BW-DEPT-03; AFR-DEPT-019-022/045."""
    student = role_client("student", kind="student", user_id=10)
    pk = post(student, "feedback", {"content": "Please replace the broken sign."}).json()["id"]
    admin = role_client("deptadmin_cse", kind="staff", user_id=11)
    assert len(admin.get(f"{BASE}/feedback").json()["results"]) == 1
    path = f"feedback/{pk}/action"
    assert post(admin, path, {"action": "review", "close_simple": True}).status_code == 409
    review = post(admin, path, {"action": "review", "category": "Signage", "close_simple": True})
    assert review.json()["status"] == "closed"
    row = Feedback.objects.get(pk=pk)
    assert row.reviewed_at <= row.disposed_at
    assert row.reviewed_by_id == row.disposed_by_id == 11
    student = role_client("student", kind="student", user_id=10)
    messages = student.get(f"{BASE}/notices").json()["results"]
    assert [message["message"] for message in messages] == [f"Feedback #{pk} was closed."]


def test_department_declines_write_when_faculty_department_is_unknown(role_client):
    faculty = role_client("faculty", department="")
    assert faculty.get(f"{BASE}/inventory").json()["results"] == []
    assert faculty.get(f"{BASE}/stock-requests").json()["results"] == []
    assert faculty.get(f"{BASE}/notices").json()["results"] == []
    assert post(faculty, "feedback", {"content": "Unknown department"}).status_code == 403
    assert not Feedback.objects.exists()


@pytest.mark.parametrize("invalid", [
    {"content": ""}, {"content": " "}, {"target_roles": ["unrecognized"]},
    {"target_batch_years": [1800]},
])
def test_invalid_announcement_never_publishes_or_notifies(role_client, invalid):
    """BR-DEPT-003; UC-DEPT-002: missing or invalid targets/content are refused."""
    faculty = role_client("faculty")
    payload = {"content": "Seminar", "target_roles": [], "target_programmes": [],
               "target_batch_years": [], **invalid}
    assert post(faculty, "announcements", payload).status_code == 400
    assert not Announcement.objects.exists()
    assert not Notice.objects.exists()


def test_overlapping_timetable_edit_preserves_published_slot(role_client):
    """UC-DEPT-009; BR-DEPT-010: an invalid edit cannot overwrite a valid slot."""
    admin = role_client("deptadmin_cse", kind="staff")
    slot = {"title": "Programming", "kind": "class", "term": "Autumn", "day": 0,
            "starts_at": "10:00", "ends_at": "11:00", "room": "R1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024}
    later = {**slot, "starts_at": "11:00", "ends_at": "12:00"}
    ids = [row["id"] for row in post(admin, "timetable", {"slots": [slot, later]}).json()]
    assert admin.put(f"{BASE}/timetable/{ids[1]}", slot, format="json").status_code == 409
    assert TimetableSlot.objects.get(pk=ids[1]).starts_at.hour == 11
    other = role_client("deptadmin_me", kind="staff", department="ME")
    assert other.put(f"{BASE}/timetable/{ids[0]}", later, format="json").status_code == 404


def test_feedback_content_never_enters_notices_and_other_departments_cannot_read(role_client):
    """BR-DEPT-017; CW-DEPT-02: confidential content stays scoped."""
    student = role_client("student", kind="student")
    secret = "Private laboratory complaint"
    assert post(student, "feedback", {"content": secret}).status_code == 201
    assert all(secret not in notice.message for notice in Notice.objects.all())
    other = role_client("deptadmin_me", kind="staff", department="ME")
    assert other.get(f"{BASE}/feedback").json()["results"] == []


def test_official_proposal_cannot_bypass_approval_or_repeat_decision(role_client):
    """BR-DEPT-011, BR-DEPT-013; CW-DEPT-03: only an approved proposal publishes."""
    admin = role_client("deptadmin_cse", kind="staff")
    proposal = {"field": "core_policies", "value": "Access hours"}
    pk = post(admin, "proposals", proposal).json()["id"]
    assert post(admin, "proposals", proposal).status_code == 409
    assert post(admin, f"proposals/{pk}/action", {"action": "approve"}).status_code == 403
    assert admin.get(f"{BASE}/details").json()["core_policies"] == ""
    hod = role_client("HOD (CSE)")
    assert post(hod, f"proposals/{pk}/action", {"action": "reject"}).status_code == 200
    assert post(hod, f"proposals/{pk}/action", {"action": "approve"}).status_code == 409
    assert hod.get(f"{BASE}/details").json()["core_policies"] == ""
