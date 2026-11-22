"""Every endpoint refuses whoever should not reach it (Steps 5.1, 5.5, 7.7)."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from core.api import csrf
from modules.department.models import Announcement, StockRequest
from modules.department.registry import NAV_ITEMS, PERMISSIONS, ROLE_GRANTS
from modules.department.tests.conftest import session_for, uid, user_refs

pytestmark = pytest.mark.django_db
API = "/api/v1/department"

ENDPOINTS = [
    ("get", "context", "department.department.view"),
    ("get", "departments", "department.department.view"),
    ("get", "departments/CSE", "department.department.view"),
    ("patch", "departments/CSE", "department.department.update"),
    ("get", "official-changes", "department.official_change.view"),
    ("post", "official-changes", "department.official_change.create"),
    ("post", "official-changes/1/decide", "department.official_change.approve"),
    ("get", "announcements", "department.announcement.view"),
    ("post", "announcements", "department.announcement.create"),
    ("patch", "announcements/1", "department.announcement.update"),
    ("delete", "announcements/1", "department.announcement.delete"),
    ("post", "announcements/1/hide", "department.announcement.update"),
    ("get", "inventory-items", "department.inventory_item.view"),
    ("post", "inventory-items", "department.inventory_item.create"),
    ("post", "inventory-items/1/receipts", "department.inventory_item.create"),
    ("get", "stock-movements", "department.stock_movement.view"),
    ("get", "stock-requests", "department.stock_request.view"),
    ("post", "stock-requests", "department.stock_request.create"),
    ("post", "stock-requests/1/decide", "department.stock_request.approve"),
    ("post", "stock-requests/1/issue", "department.stock_issue.create"),
    ("get", "feedback", "department.feedback.view"),
    ("post", "feedback", "department.feedback.create"),
    ("get", "feedback/1", "department.feedback.view"),
    ("post", "feedback/1/review", "department.feedback.review"),
    ("post", "feedback/1/dispose", "department.feedback_resolution.create"),
    ("post", "feedback/1/notes", "department.feedback_resolution.create"),
    ("get", "timetable-slots", "department.timetable.view"),
    ("post", "timetable-slots", "department.timetable.create"),
    ("patch", "timetable-slots/1", "department.timetable.update"),
    ("delete", "timetable-slots/1", "department.timetable.update"),
    ("get", "lab-resources", "department.lab_resource.view"),
    ("post", "lab-resources", "department.lab_resource.update"),
    ("patch", "lab-resources/1", "department.lab_resource.update"),
    ("get", "profiles", "department.profile.view"),
    ("get", "profiles/1", "department.profile.view"),
    ("post", "profiles", "department.profile.update"),
    ("patch", "profiles/1", "department.profile.update"),
    ("get", "role-assignments", "department.role_assignment.view"),
    ("get", "role-assignments/vacancies", "department.role_assignment.view"),
    ("post", "role-assignments", "department.role_assignment.assign"),
    ("patch", "role-assignments/1", "department.role_assignment.assign"),
]
DECLARED = {code for code, _ in PERMISSIONS}


def _client(stub_iam, session):
    stub_iam(session)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_every_code_used_here_and_in_grants_is_declared():
    """A typo'd code is granted by the fake and denied in production."""
    used = {code for _, _, code in ENDPOINTS}
    granted = {c for codes in ROLE_GRANTS.values() for c in codes}
    navs = {item["required_permission"] for item in NAV_ITEMS}
    assert used | granted | navs <= DECLARED
    assert (
        DECLARED - {"department.role_assignment.update"} <= used | navs
    )  # every code guards something


def test_every_url_is_in_the_endpoint_table():
    from modules.department.api.urls import urlpatterns

    routed = {re.sub(r"<\w+:\w+>", "X", str(p.pattern)) for p in urlpatterns}
    listed = {re.sub(r"\d+|CSE", "X", path) for _, path, _ in ENDPOINTS}
    assert routed == listed


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_module_grant_without_the_permission_is_403(world, stub_iam, method, path, code):
    everything_else = DECLARED - {code}
    c = _client(stub_iam, session_for("hod", permissions=everything_else))
    assert getattr(c, method)(f"{API}/{path}", {}, format="json").status_code == 403


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_permission_without_the_module_grant_is_403(world, stub_iam, method, path, code):
    c = _client(stub_iam, session_for("hod", permissions=DECLARED, modules=("placement_cell",)))
    assert getattr(c, method)(f"{API}/{path}", {}, format="json").status_code == 403


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_no_session_is_401(world, stub_iam, method, path, code):
    stub_iam(None)
    r = getattr(APIClient(), method)(f"{API}/{path}", {}, format="json")
    assert r.status_code == 401


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_plain_user_of_another_office_gets_nothing(world, stub_iam, method, path, code):
    """Step 5.2: the ordinary staff member with no department grant at all."""
    c = _client(stub_iam, session_for("outsider", modules=()))
    assert getattr(c, method)(f"{API}/{path}", {}, format="json").status_code == 403


STUDENT_DENIED = [e for e in ENDPOINTS if e[2] not in ROLE_GRANTS["student"]]


@pytest.mark.parametrize(("method", "path", "code"), STUDENT_DENIED)
def test_student_role_reaches_none_of_the_office_endpoints(world, act, method, path, code):
    assert getattr(act("student"), method)(f"{API}/{path}", {}, format="json").status_code == 403


def test_hod_acting_as_faculty_gets_the_faculty_view_only(world, act):
    """Step 5.1: only the acting role counts (rbac-model.md, property 2)."""
    act("admin").post(f"{API}/inventory-items", {"name": "Kit", "quantity": 5}, format="json")
    item = act("admin").get(f"{API}/inventory-items").json()["results"][0]["id"]
    req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
        .json()["id"]
    )
    # The IAM sends the union of held permissions; the acting role still decides the rows.
    as_faculty = act("hod", active_role="faculty")
    r = as_faculty.post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
    assert r.status_code == 404
    assert as_faculty.get(f"{API}/stock-requests").json()["results"] == []
    assert StockRequest.objects.get(pk=req).status == "pending_hod"


def test_faculty_cannot_maintain_an_announcement_they_wrote(world, act):
    # BR-DEPT-004: only the HOD edits, hides or deletes
    aid = (
        act("faculty")
        .post(
            f"{API}/announcements",
            {"title": "t", "body": "b", "audience_role": "all"},
            format="json",
        )
        .json()["id"]
    )
    c = act("faculty")
    assert c.patch(f"{API}/announcements/{aid}", {"title": "x"}, format="json").status_code == 403
    assert c.delete(f"{API}/announcements/{aid}").status_code == 403
    assert Announcement.objects.get(pk=aid).title == "t"


def test_dept_admin_cannot_approve_and_hod_cannot_issue(world, act):
    # BR-DEPT-006, BR-DEPT-007: the verbs belong to different offices
    act("admin").post(f"{API}/inventory-items", {"name": "Kit", "quantity": 5}, format="json")
    item = act("admin").get(f"{API}/inventory-items").json()["results"][0]["id"]
    req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
        .json()["id"]
    )
    assert (
        act("admin")
        .post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
        .status_code
        == 403
    )
    act("hod").post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
    assert act("hod").post(f"{API}/stock-requests/{req}/issue").status_code == 403


def test_only_the_central_authority_assigns_roles(world, act):
    # BR-DEPT-021
    body = {
        "department": "CSE",
        "role": "hod",
        "user_id": uid("faculty"),
        "valid_from": "2030-01-01T00:00:00Z",
        "valid_to": "2031-01-01T00:00:00Z",
    }
    for who in ("hod", "admin", "faculty"):
        assert act(who).post(f"{API}/role-assignments", body, format="json").status_code == 403


def test_a_principal_with_a_designation_but_no_tenure_sees_no_rows(world, act):
    # Q1: the designation gives the verb, only an in-effect tenure gives the rows
    act("faculty").post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
    c = act("next_hod")
    assert c.get(f"{API}/feedback").json()["results"] == []
    r = c.post(
        f"{API}/announcements", {"title": "t", "body": "b", "audience_role": "all"}, format="json"
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "no_department"


def test_cookie_write_without_csrf_token_is_403(world, stub_iam):
    stub_iam(session_for("faculty"), users=user_refs())
    c = APIClient()
    c.cookies[settings.IAM_AUTH_COOKIE_NAME] = "sess-1"
    body = {"title": "t", "body": "b", "audience_role": "all"}
    assert c.post(f"{API}/announcements", body, format="json").status_code == 403
    ok = c.post(
        f"{API}/announcements", body, format="json", HTTP_X_CSRF_TOKEN=csrf.token_for("sess-1")
    )
    assert ok.status_code == 201
    assert Announcement.objects.count() == 1


def test_no_view_loosens_authentication_or_permissions():
    src = (Path(__file__).resolve().parents[1] / "api" / "views.py").read_text()
    assert "AllowAny" not in src and "authentication_classes" not in src


GETS = [e for e in ENDPOINTS if e[0] == "get"]


@pytest.mark.parametrize(("method", "path", "code"), GETS)
def test_head_and_options_need_the_read_permission_too(world, stub_iam, method, path, code):
    # R1-01: HEAD and OPTIONS run the GET gate, so they cannot probe for rows
    c = _client(stub_iam, session_for("hod", permissions=DECLARED - {code}))
    assert c.head(f"{API}/{path}").status_code == 403
    assert c.options(f"{API}/{path}").status_code == 403


def test_a_method_without_a_named_permission_is_refused(world, act):
    # R1-01: an unmapped method fails closed instead of falling through to the module gate
    r = act("hod").put(f"{API}/announcements/1", {}, format="json")
    assert r.status_code in (403, 405)
    assert act("hod").post(f"{API}/departments", {}, format="json").status_code in (403, 405)


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_each_view_asks_for_exactly_the_permission_its_endpoint_needs(method, path, code):
    # R3-04: a view whose permission is weakened (say update -> view) fails here, whatever else it checks
    from django.urls import resolve

    view = resolve(f"{API}/{path}").func.view_class
    assert view.perms.get(method.upper()) == code, (path, method, view.perms)
