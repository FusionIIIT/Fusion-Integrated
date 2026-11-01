"""The business rules, end to end through HTTP."""
from dataclasses import replace

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.dept import registry
from modules.dept.models import Announcement, InventoryItem, StockMovement

pytestmark = pytest.mark.django_db

HOD, ADMIN, FACULTY, STUDENT = 10, 20, 30, 40


def _as(stub_iam, role, user_id, users=None):
    """Sign in with exactly the permissions the registry grants that role."""
    kind = "student" if role == "student" else "faculty"
    stub_iam(make_session(user_id=user_id, kind=kind, roles=(role,),
                          active_role=role, modules=("dept",),
                          permissions=registry.ROLE_GRANTS[role]),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def item():
    return InventoryItem.objects.create(name="Oscilloscope", quantity=5)


# -- announcements -----------------------------------------------------------------
def test_student_cannot_publish_announcement(stub_iam):     # BR-DEPT-001
    r = _as(stub_iam, "student", STUDENT).post(
        "/api/v1/dept/announcements", {"title": "t", "body": "b"}, format="json")
    assert r.status_code == 403


def test_faculty_publishes_and_incomplete_is_blocked(stub_iam):
    c = _as(stub_iam, "faculty", FACULTY)
    ok = c.post("/api/v1/dept/announcements",
                {"title": "Lab", "body": "Moved", "target_roles": ["student"]},
                format="json")
    assert ok.status_code == 201
    bad = c.post("/api/v1/dept/announcements",
                 {"title": "Lab", "body": " "}, format="json")
    assert bad.status_code == 400          # blank body rejected at the edge
    unknown = c.post("/api/v1/dept/announcements",
                     {"title": "t", "body": "b", "target_roles": ["janitor"]},
                     format="json")
    assert unknown.status_code == 409
    assert unknown.json()["error"]["code"] == "announcement_incomplete"


def test_student_only_sees_announcements_targeting_them(stub_iam, user_ref):
    Announcement.objects.create(title="all", body="b", published_by_user_id=1)
    Announcement.objects.create(title="faculty only", body="b",
                                target_roles=["faculty"], published_by_user_id=1)
    Announcement.objects.create(title="2023 batch", body="b",
                                target_years=[2023], published_by_user_id=1)
    me = replace(user_ref(STUDENT), batch_year=2024)
    titles = {a["title"] for a in _as(stub_iam, "student", STUDENT,
                                      {STUDENT: me}).get(
        "/api/v1/dept/announcements").json()}
    assert titles == {"all"}


def test_only_hod_can_hide_and_hidden_disappears(stub_iam):  # BR-DEPT-004
    a = Announcement.objects.create(title="x", body="b", published_by_user_id=1)
    url = f"/api/v1/dept/announcements/{a.pk}/status"
    assert _as(stub_iam, "dept_admin", ADMIN).post(
        url, {"status": "hidden"}, format="json").status_code == 403
    assert _as(stub_iam, "hod", HOD).post(
        url, {"status": "hidden"}, format="json").status_code == 200
    assert _as(stub_iam, "dept_admin", ADMIN).get(
        "/api/v1/dept/announcements").json() == []


def test_hod_delete_is_soft(stub_iam):
    a = Announcement.objects.create(title="x", body="b", published_by_user_id=1)
    assert _as(stub_iam, "hod", HOD).delete(
        f"/api/v1/dept/announcements/{a.pk}").status_code == 200
    a.refresh_from_db()
    assert a.status == "deleted"


# -- stock -------------------------------------------------------------------------
def test_inventory_insertion_is_logged_and_dept_admin_only(stub_iam):
    body = {"name": "Multimeter", "quantity": 4}
    assert _as(stub_iam, "faculty", FACULTY).post(
        "/api/v1/dept/inventory", body, format="json").status_code == 403
    r = _as(stub_iam, "dept_admin", ADMIN).post(
        "/api/v1/dept/inventory", body, format="json")
    assert r.status_code == 201 and r.json()["quantity"] == 4
    assert StockMovement.objects.filter(kind="insert", quantity=4).count() == 1


def test_request_beyond_stock_is_blocked(stub_iam, item):    # BR-DEPT-015
    r = _as(stub_iam, "faculty", FACULTY).post(
        "/api/v1/dept/stock-requests", {"item": item.pk, "quantity": 6},
        format="json")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "insufficient_stock"


def test_only_faculty_can_request(stub_iam, item):           # BR-DEPT-005
    r = _as(stub_iam, "dept_admin", ADMIN).post(
        "/api/v1/dept/stock-requests", {"item": item.pk, "quantity": 1},
        format="json")
    assert r.status_code == 403


def _request(stub_iam, item, qty=2):
    r = _as(stub_iam, "faculty", FACULTY).post(
        "/api/v1/dept/stock-requests", {"item": item.pk, "quantity": qty},
        format="json")
    assert r.status_code == 201
    return r.json()["id"]


def test_full_stock_lifecycle_decrements_and_logs(stub_iam, item):
    rid = _request(stub_iam, item, 2)

    # cannot issue before the HOD approves (BR-DEPT-007)
    early = _as(stub_iam, "dept_admin", ADMIN).post(
        f"/api/v1/dept/stock-requests/{rid}/issue")
    assert early.status_code == 409

    # Dept_Admin may not approve (BR-DEPT-006)
    assert _as(stub_iam, "dept_admin", ADMIN).post(
        f"/api/v1/dept/stock-requests/{rid}/decision", {"approve": True},
        format="json").status_code == 403

    assert _as(stub_iam, "hod", HOD).post(
        f"/api/v1/dept/stock-requests/{rid}/decision", {"approve": True},
        format="json").json()["status"] == "approved"

    issued = _as(stub_iam, "dept_admin", ADMIN).post(
        f"/api/v1/dept/stock-requests/{rid}/issue")
    assert issued.status_code == 200 and issued.json()["status"] == "issued"

    item.refresh_from_db()
    assert item.quantity == 3
    assert StockMovement.objects.filter(kind="issue", quantity=2).count() == 1

    # faculty see their issued history
    hist = _as(stub_iam, "faculty", FACULTY).get(
        "/api/v1/dept/stock-requests/issued").json()
    assert [h["id"] for h in hist] == [rid]


def test_rejected_request_cannot_be_issued(stub_iam, item):
    rid = _request(stub_iam, item)
    _as(stub_iam, "hod", HOD).post(
        f"/api/v1/dept/stock-requests/{rid}/decision", {"approve": False},
        format="json")
    assert _as(stub_iam, "dept_admin", ADMIN).post(
        f"/api/v1/dept/stock-requests/{rid}/issue").status_code == 409


def test_issue_is_blocked_when_stock_ran_out_since(stub_iam, item):
    rid = _request(stub_iam, item, 4)
    _as(stub_iam, "hod", HOD).post(
        f"/api/v1/dept/stock-requests/{rid}/decision", {"approve": True},
        format="json")
    InventoryItem.objects.filter(pk=item.pk).update(quantity=1)
    r = _as(stub_iam, "dept_admin", ADMIN).post(
        f"/api/v1/dept/stock-requests/{rid}/issue")
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_stock"
    item.refresh_from_db()
    assert item.quantity == 1


def test_faculty_only_sees_their_own_requests(stub_iam, item):
    _request(stub_iam, item)
    assert _as(stub_iam, "faculty", 31).get(
        "/api/v1/dept/stock-requests").json() == []


def test_stock_movements_are_immutable(item):                # BR-DEPT-016
    m = StockMovement.objects.create(item=item, kind="insert", quantity=1,
                                     actor_user_id=1)
    m.quantity = 99
    with pytest.raises(RuntimeError):
        m.save()
    with pytest.raises(RuntimeError):
        m.delete()
    with pytest.raises(RuntimeError):
        StockMovement.objects.all().update(quantity=0)
    with pytest.raises(RuntimeError):
        StockMovement.objects.all().delete()


# -- feedback ----------------------------------------------------------------------
def _submit(stub_iam, user=STUDENT, role="student"):
    r = _as(stub_iam, role, user).post(
        "/api/v1/dept/feedback", {"subject": "Wi-Fi", "body": "Down in lab 2"},
        format="json")
    assert r.status_code == 201
    return r.json()["id"]


def test_dept_admin_cannot_submit_feedback(stub_iam):        # BR-DEPT-008
    assert _as(stub_iam, "dept_admin", ADMIN).post(
        "/api/v1/dept/feedback", {"subject": "s", "body": "b"},
        format="json").status_code == 403


def test_feedback_is_confidential_to_submitter(stub_iam):    # BR-DEPT-017
    _submit(stub_iam)
    assert _as(stub_iam, "student", 41).get("/api/v1/dept/feedback").json() == []
    assert len(_as(stub_iam, "student", STUDENT).get(
        "/api/v1/dept/feedback").json()) == 1
    assert len(_as(stub_iam, "dept_admin", ADMIN).get(
        "/api/v1/dept/feedback").json()) == 1


def test_hod_cannot_see_feedback_before_initial_review(stub_iam):  # BR-DEPT-018
    fid = _submit(stub_iam)
    hod = _as(stub_iam, "hod", HOD)
    assert hod.get("/api/v1/dept/feedback").json() == []
    assert hod.post(f"/api/v1/dept/feedback/{fid}/transition",
                    {"to_status": "resolved", "note": "x"},
                    format="json").status_code == 404

    admin = _as(stub_iam, "dept_admin", ADMIN)
    assert admin.post(f"/api/v1/dept/feedback/{fid}/transition",
                      {"to_status": "under_review", "category": "IT"},
                      format="json").status_code == 200
    assert len(_as(stub_iam, "hod", HOD).get("/api/v1/dept/feedback").json()) == 1


def test_initial_review_requires_category_and_disposal_requires_note(stub_iam):
    fid = _submit(stub_iam)
    admin = _as(stub_iam, "dept_admin", ADMIN)
    url = f"/api/v1/dept/feedback/{fid}/transition"
    assert admin.post(url, {"to_status": "under_review"},
                      format="json").json()["error"]["code"] == "category_required"
    admin.post(url, {"to_status": "under_review", "category": "IT"}, format="json")
    assert admin.post(url, {"to_status": "closed"},
                      format="json").json()["error"]["code"] == "note_required"


def test_hod_can_resolve_after_review_and_terminal_is_final(stub_iam):  # BR-009
    fid = _submit(stub_iam)
    url = f"/api/v1/dept/feedback/{fid}/transition"
    _as(stub_iam, "dept_admin", ADMIN).post(
        url, {"to_status": "under_review", "category": "IT"}, format="json")
    done = _as(stub_iam, "hod", HOD).post(
        url, {"to_status": "resolved", "note": "Router replaced"}, format="json")
    assert done.status_code == 200 and done.json()["status"] == "resolved"
    again = _as(stub_iam, "dept_admin", ADMIN).post(
        url, {"to_status": "closed", "note": "n"}, format="json")
    assert again.status_code == 409


def test_student_cannot_move_feedback(stub_iam):
    fid = _submit(stub_iam)
    assert _as(stub_iam, "student", STUDENT).post(
        f"/api/v1/dept/feedback/{fid}/transition",
        {"to_status": "closed", "note": "n"}, format="json").status_code == 403


def test_unauthenticated_gets_401(stub_iam):
    stub_iam(None)
    assert APIClient().get("/api/v1/dept/announcements").status_code in (401, 403)
