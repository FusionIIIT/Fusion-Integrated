"""API tests for leave, bonafide, seminar and the supervisor / TA records.

Every person needs a department: the services refuse when it is unknown.
"""
import dataclasses

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.oap.domain import bonafide as bonafide_rules
from modules.oap.domain import leave as leave_rules
from modules.oap.domain import seminar as seminar_rules
from modules.oap.models import Notification

pytestmark = pytest.mark.django_db

BASE = "/api/v1/oap/"

STUDENT_LEAVE = ("oap.leave.submit", "oap.leave.view_self")
STUDENT_BONAFIDE = ("oap.bonafide.submit", "oap.bonafide.view_self")


@pytest.fixture
def people(user_ref):
    """{user_id: UserRef} for everyone in these tests."""

    def person(uid, department, programme="", kind="student"):
        # UserRef is a frozen dataclass, so build a modified copy.
        return dataclasses.replace(
            user_ref(uid, kind=kind), department=department, programme=programme
        )

    return {
        1001: person(1001, "CSE", "B.Tech"),
        1002: person(1002, "CSE", "B.Tech"),
        1003: person(1003, "CSE", "M.Tech"),
        2001: person(2001, "CSE", kind="faculty"),  # HoD
        2002: person(2002, "ECE", kind="faculty"),  # HoD, other department
        3001: person(3001, "ACAD", kind="staff"),  # Academic Admin
        4001: person(4001, "CSE", kind="staff"),  # Department Admin
        4002: person(4002, "ECE", kind="staff"),  # Department Admin, other dept
        5001: person(5001, "CSE", kind="faculty"),
    }


def login(stub_iam, user_id, perms, users, modules=("oap",)):
    stub_iam(
        make_session(user_id=user_id, modules=modules, permissions=perms),
        users=users,
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _leave_body(**overrides):
    body = {
        "start_date": "2026-12-01",
        "end_date": "2026-12-05",
        "reason": "Family function",
    }
    body.update(overrides)
    return body


def submit_leave(stub_iam, users, user_id=1001):
    c = login(stub_iam, user_id, STUDENT_LEAVE, users)
    r = c.post(BASE + "leave/", _leave_body(), format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def submit_bonafide(stub_iam, users, user_id=1001):
    c = login(stub_iam, user_id, STUDENT_BONAFIDE, users)
    r = c.post(BASE + "bonafide/", {"purpose": "Visa application"}, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def submit_seminar(stub_iam, users, user_id=1003):
    c = login(stub_iam, user_id, ("oap.seminar.request",), users)
    r = c.post(BASE + "seminar/", {}, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


# -- Leave ---------------------------------------------------------------------
def test_student_submits_leave(stub_iam, people):
    c = login(stub_iam, 1001, STUDENT_LEAVE, people)
    r = c.post(BASE + "leave/", _leave_body(), format="json")

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == leave_rules.SUBMITTED
    notes = Notification.objects.filter(recipient_id=1001, case_id=body["id"])
    assert notes.count() == 2
    assert {n.channel for n in notes} == {"alert", "email"}


def test_leave_start_after_end_is_400(stub_iam, people):
    c = login(stub_iam, 1001, STUDENT_LEAVE, people)
    r = c.post(
        BASE + "leave/",
        _leave_body(start_date="2026-12-10", end_date="2026-12-01"),
        format="json",
    )
    assert r.status_code == 400


def test_student_lists_only_their_own_leave(stub_iam, people):
    mine = submit_leave(stub_iam, people, 1001)
    submit_leave(stub_iam, people, 1002)

    c = login(stub_iam, 1001, STUDENT_LEAVE, people)
    rows = c.get(BASE + "leave/").json()["results"]
    assert [row["id"] for row in rows] == [mine]
    assert all(row["student_id"] == 1001 for row in rows)


def test_hod_sees_and_approves_leave_once(stub_iam, people):
    pk = submit_leave(stub_iam, people)

    hod = login(stub_iam, 2001, ("oap.leave.decide",), people)
    pending = hod.get(BASE + "leave/pending/").json()["results"]
    assert pk in [row["id"] for row in pending]

    r = hod.post(f"{BASE}leave/{pk}/decision/", {"action": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == leave_rules.APPROVED

    again = hod.post(f"{BASE}leave/{pk}/decision/", {"action": "reject"},
                     format="json")
    assert again.status_code == 400


def test_other_department_hod_cannot_see_or_decide(stub_iam, people):
    pk = submit_leave(stub_iam, people)

    hod = login(stub_iam, 2002, ("oap.leave.decide",), people)
    pending = hod.get(BASE + "leave/pending/").json()["results"]
    assert pk not in [row["id"] for row in pending]

    r = hod.post(f"{BASE}leave/{pk}/decision/", {"action": "approve"}, format="json")
    assert r.status_code == 404


def test_user_without_the_oap_module_gets_403(stub_iam, people):
    c = login(stub_iam, 1001, ("oap.leave.view_self",), people, modules=())
    assert c.get(BASE + "leave/").status_code == 403


def test_student_cannot_call_the_decision_endpoint(stub_iam, people):
    pk = submit_leave(stub_iam, people)
    c = login(stub_iam, 1001, STUDENT_LEAVE, people)
    r = c.post(f"{BASE}leave/{pk}/decision/", {"action": "approve"}, format="json")
    assert r.status_code == 403


def test_leave_detail_shows_history_and_hides_foreign_rows(stub_iam, people):
    pk = submit_leave(stub_iam, people, 1001)
    other = submit_leave(stub_iam, people, 1002)

    hod = login(stub_iam, 2001, ("oap.leave.decide",), people)
    hod.post(f"{BASE}leave/{pk}/decision/", {"action": "approve"}, format="json")

    c = login(stub_iam, 1001, STUDENT_LEAVE, people)
    r = c.get(f"{BASE}leave/{pk}/")
    assert r.status_code == 200
    actions = [e["action"] for e in r.json()["history"]]
    assert actions[0] == "submit"
    assert "approve" in actions

    assert c.get(f"{BASE}leave/{other}/").status_code == 404


# -- Bonafide ------------------------------------------------------------------
def test_bonafide_approval_issues_a_certificate(stub_iam, people):
    pk = submit_bonafide(stub_iam, people)

    admin = login(stub_iam, 3001, ("oap.bonafide.decide",), people)
    r = admin.post(f"{BASE}bonafide/{pk}/decision/", {"action": "approve"},
                   format="json")
    assert r.status_code == 200
    assert r.json()["status"] == bonafide_rules.APPROVED

    student = login(stub_iam, 1001, STUDENT_BONAFIDE, people)
    cert = student.get(f"{BASE}bonafide/{pk}/certificate/")
    assert cert.status_code == 200
    assert cert.json()["certificate_number"].startswith("BON-")
    assert cert.json()["student_id"] == 1001


def test_bonafide_certificate_before_approval_is_400(stub_iam, people):
    pk = submit_bonafide(stub_iam, people)
    student = login(stub_iam, 1001, STUDENT_BONAFIDE, people)
    assert student.get(f"{BASE}bonafide/{pk}/certificate/").status_code == 400


def test_bonafide_certificate_of_another_student_is_404(stub_iam, people):
    pk = submit_bonafide(stub_iam, people, 1001)

    admin = login(stub_iam, 3001, ("oap.bonafide.decide",), people)
    admin.post(f"{BASE}bonafide/{pk}/decision/", {"action": "approve"},
               format="json")

    other = login(stub_iam, 1002, STUDENT_BONAFIDE, people)
    assert other.get(f"{BASE}bonafide/{pk}/certificate/").status_code == 404


def test_bonafide_certificate_after_reject_is_400(stub_iam, people):
    pk = submit_bonafide(stub_iam, people)

    admin = login(stub_iam, 3001, ("oap.bonafide.decide",), people)
    r = admin.post(f"{BASE}bonafide/{pk}/decision/", {"action": "reject"},
                   format="json")
    assert r.json()["status"] == bonafide_rules.REJECTED

    student = login(stub_iam, 1001, STUDENT_BONAFIDE, people)
    assert student.get(f"{BASE}bonafide/{pk}/certificate/").status_code == 400


# -- Seminar -------------------------------------------------------------------
def test_pg_student_can_request_a_seminar(stub_iam, people):
    c = login(stub_iam, 1003, ("oap.seminar.request",), people)
    r = c.post(BASE + "seminar/", {}, format="json")
    assert r.status_code == 201
    assert r.json()["status"] == seminar_rules.INITIAL_STATE


def test_ug_student_cannot_request_a_seminar(stub_iam, people):
    c = login(stub_iam, 1001, ("oap.seminar.request",), people)
    r = c.post(BASE + "seminar/", {}, format="json")
    assert r.status_code == 400


def test_department_admin_schedules_a_seminar(stub_iam, people):
    pk = submit_seminar(stub_iam, people)

    admin = login(stub_iam, 4001, ("oap.seminar.schedule",), people)
    r = admin.post(
        f"{BASE}seminar/{pk}/schedule/",
        {"scheduled_at": "2026-12-10T10:00:00Z", "venue": "LHC 101"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == seminar_rules.SCHEDULED
    assert r.json()["venue"] == "LHC 101"

    faculty = login(stub_iam, 5001, ("oap.seminar.view",), people)
    rows = faculty.get(BASE + "seminar/schedule/").json()["results"]
    assert pk in [row["id"] for row in rows]


def test_scheduling_without_a_time_is_400(stub_iam, people):
    pk = submit_seminar(stub_iam, people)
    admin = login(stub_iam, 4001, ("oap.seminar.schedule",), people)
    r = admin.post(f"{BASE}seminar/{pk}/schedule/", {"venue": "LHC 101"},
                   format="json")
    assert r.status_code == 400


def test_other_department_admin_cannot_schedule(stub_iam, people):
    pk = submit_seminar(stub_iam, people)
    admin = login(stub_iam, 4002, ("oap.seminar.schedule",), people)
    r = admin.post(
        f"{BASE}seminar/{pk}/schedule/",
        {"scheduled_at": "2026-12-10T10:00:00Z"},
        format="json",
    )
    assert r.status_code == 404


# -- Records -------------------------------------------------------------------
def test_department_admin_records_supervisor_and_ta(stub_iam, people):
    admin = login(stub_iam, 4001, ("oap.assignment.manage",), people)

    r = admin.post(
        BASE + "records/supervisor/",
        {"student_id": 1003, "faculty_id": 5001},
        format="json",
    )
    assert r.status_code == 201

    # A course-only TA assignment is allowed.
    r = admin.post(
        BASE + "records/ta/",
        {"student_id": 1003, "course_code": "CS101"},
        format="json",
    )
    assert r.status_code == 201


def test_ta_assignment_needs_a_course_or_a_faculty_member(stub_iam, people):
    admin = login(stub_iam, 4001, ("oap.assignment.manage",), people)
    r = admin.post(BASE + "records/ta/", {"student_id": 1003}, format="json")
    assert r.status_code == 400


def test_other_department_admin_cannot_record_for_the_student(stub_iam, people):
    admin = login(stub_iam, 4002, ("oap.assignment.manage",), people)
    r = admin.post(
        BASE + "records/supervisor/",
        {"student_id": 1003, "faculty_id": 5001},
        format="json",
    )
    assert r.status_code == 400
