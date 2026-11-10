"""API tests for no-dues clearance (CW-OAP-03) and assistantship claims
(CW-OAP-04).

Every person needs a department: the services refuse when it is unknown.
"""
import dataclasses

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.oap.domain import assistantship as assistantship_rules
from modules.oap.domain import nodues as nodues_rules
from modules.oap.models import AssistantshipClaim, Notification

pytestmark = pytest.mark.django_db

BASE = "/api/v1/oap/"

STUDENT_NODUES = ("oap.nodues.submit", "oap.nodues.view_self")
STUDENT_CLAIM = ("oap.assistantship.submit", "oap.assistantship.view_self")

#: One authority per no-dues domain; each holds only its own verify permission.
AUTHORITY = {
    "library": 6001,
    "hostel": 6002,
    "mess": 6003,
    "department": 6004,
    "lab": 6005,
    "academic_section": 6006,
    "student_section": 6007,
}


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
        1003: person(1003, "CSE", "M.Tech"),
        1004: person(1004, "CSE", "M.Tech"),
        1005: person(1005, "CSE", "M.Tech"),
        6001: person(6001, "LIB", kind="staff"),  # Librarian
        6002: person(6002, "HOSTEL", kind="staff"),  # Hostel Warden
        6003: person(6003, "MESS", kind="staff"),  # Mess In-charge
        6004: person(6004, "CSE", kind="staff"),  # Department Verifier
        6005: person(6005, "LAB", kind="staff"),  # Lab Supervisor
        6006: person(6006, "ACAD", kind="staff"),  # Academic Section Verifier
        6007: person(6007, "SS", kind="staff"),  # Student Section Verifier
        6008: person(6008, "ECE", kind="staff"),  # Department Verifier, other dept
        3001: person(3001, "ACAD", kind="staff"),  # Academic Admin
        4001: person(4001, "CSE", kind="staff"),  # Department Admin
        2001: person(2001, "CSE", kind="faculty"),  # HoD
        2002: person(2002, "ECE", kind="faculty"),  # HoD, other department
        5001: person(5001, "CSE", kind="faculty"),
        5002: person(5002, "CSE", kind="faculty"),
        5003: person(5003, "CSE", kind="faculty"),
        5009: person(5009, "CSE", kind="faculty"),  # not assigned to anyone
    }


def login(stub_iam, user_id, perms, users, modules=("oap",)):
    stub_iam(
        make_session(user_id=user_id, modules=modules, permissions=perms),
        users=users,
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


# -- No-dues helpers -----------------------------------------------------------
def submit_nodues(stub_iam, users, user_id=1001):
    c = login(stub_iam, user_id, STUDENT_NODUES, users)
    r = c.post(BASE + "nodues/", {}, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def record(stub_iam, users, pk, domain_code, result, actor_id=None):
    """The authority for `domain_code` records a result, with only its own
    verify permission."""
    actor_id = actor_id or AUTHORITY[domain_code]
    perms = (nodues_rules.VERIFY_PERMISSIONS[domain_code],)
    c = login(stub_iam, actor_id, perms, users)
    return c.post(
        f"{BASE}nodues/{pk}/clearance/{domain_code}/",
        {"result": result},
        format="json",
    )


def record_all(stub_iam, users, pk, overrides=None):
    overrides = overrides or {}
    last = None
    for code in nodues_rules.DOMAIN_CODES:
        last = record(
            stub_iam, users, pk, code, overrides.get(code, nodues_rules.RESULT_CLEAR)
        )
        assert last.status_code == 200, last.content
    return last


def get_request(stub_iam, users, pk, user_id=1001):
    c = login(stub_iam, user_id, STUDENT_NODUES, users)
    return c.get(f"{BASE}nodues/{pk}/")


# -- No-dues -------------------------------------------------------------------
def test_student_submits_nodues_to_all_seven_authorities(stub_iam, people):
    pk = submit_nodues(stub_iam, people)

    r = get_request(stub_iam, people, pk)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == nodues_rules.IN_PROGRESS
    assert [c["domain_code"] for c in body["clearances"]] == nodues_rules.DOMAIN_CODES
    assert len(body["clearances"]) == 7
    assert all(c["result"] == nodues_rules.RESULT_PENDING for c in body["clearances"])


def test_second_nodues_submission_while_open_is_400(stub_iam, people):
    submit_nodues(stub_iam, people)
    c = login(stub_iam, 1001, STUDENT_NODUES, people)
    assert c.post(BASE + "nodues/", {}, format="json").status_code == 400


def test_authority_records_only_its_own_domain(stub_iam, people):
    pk = submit_nodues(stub_iam, people)

    r = record(stub_iam, people, pk, "library", nodues_rules.RESULT_CLEAR)
    assert r.status_code == 200
    rows = {c["domain_code"]: c["result"] for c in r.json()["clearances"]}
    assert rows["library"] == nodues_rules.RESULT_CLEAR
    assert rows["lab"] == nodues_rules.RESULT_PENDING
    assert r.json()["status"] == nodues_rules.IN_PROGRESS

    # The Librarian holds no permission for the lab domain.
    librarian = login(
        stub_iam, 6001, (nodues_rules.VERIFY_PERMISSIONS["library"],), people
    )
    r = librarian.post(
        f"{BASE}nodues/{pk}/clearance/lab/",
        {"result": nodues_rules.RESULT_CLEAR},
        format="json",
    )
    assert r.status_code == 403

    r = librarian.post(
        f"{BASE}nodues/{pk}/clearance/canteen/",
        {"result": nodues_rules.RESULT_CLEAR},
        format="json",
    )
    assert r.status_code == 404


def test_a_recorded_result_is_not_overwritten(stub_iam, people):
    pk = submit_nodues(stub_iam, people)
    assert record(stub_iam, people, pk, "library",
                  nodues_rules.RESULT_CLEAR).status_code == 200
    again = record(stub_iam, people, pk, "library", nodues_rules.RESULT_DUES)
    assert again.status_code == 400


def test_department_verifier_must_belong_to_the_students_department(stub_iam, people):
    pk = submit_nodues(stub_iam, people)

    other = record(stub_iam, people, pk, "department", nodues_rules.RESULT_CLEAR,
                   actor_id=6008)
    assert other.status_code == 404

    own = record(stub_iam, people, pk, "department", nodues_rules.RESULT_CLEAR,
                 actor_id=6004)
    assert own.status_code == 200


def test_all_clear_then_finalize_issues_a_certificate(stub_iam, people):
    pk = submit_nodues(stub_iam, people)
    before = Notification.objects.filter(
        recipient_id=1001, case_type="nodues", case_id=pk
    ).count()

    last = record_all(stub_iam, people, pk)
    assert last.json()["status"] == nodues_rules.ALL_CLEAR
    after = Notification.objects.filter(
        recipient_id=1001, case_type="nodues", case_id=pk
    ).count()
    assert after == before + 2  # a completion alert and email

    admin = login(stub_iam, 3001, ("oap.nodues.finalize",), people)
    completed = admin.get(BASE + "nodues/completed/").json()["results"]
    assert pk in [row["id"] for row in completed]

    r = admin.post(f"{BASE}nodues/{pk}/finalize/", {}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == nodues_rules.FINALIZED

    student = login(stub_iam, 1001, STUDENT_NODUES, people)
    cert = student.get(f"{BASE}nodues/{pk}/certificate/")
    assert cert.status_code == 200
    assert cert.json()["certificate_number"].startswith("NDC-")


def test_dues_outstanding_blocks_finalize_and_certificate(stub_iam, people):
    pk = submit_nodues(stub_iam, people)
    last = record_all(stub_iam, people, pk, {"mess": nodues_rules.RESULT_DUES})
    assert last.json()["status"] == nodues_rules.DUES_OUTSTANDING

    admin = login(stub_iam, 3001, ("oap.nodues.finalize",), people)
    assert admin.post(f"{BASE}nodues/{pk}/finalize/", {},
                      format="json").status_code == 400

    student = login(stub_iam, 1001, STUDENT_NODUES, people)
    assert student.get(f"{BASE}nodues/{pk}/certificate/").status_code == 400


def test_certificate_is_unavailable_until_finalized_and_private(stub_iam, people):
    pk = submit_nodues(stub_iam, people)

    owner = login(stub_iam, 1001, STUDENT_NODUES, people)
    assert owner.get(f"{BASE}nodues/{pk}/certificate/").status_code == 400

    other = login(stub_iam, 1003, STUDENT_NODUES, people)
    assert other.get(f"{BASE}nodues/{pk}/certificate/").status_code == 404


def test_pending_list_drops_a_request_once_the_authority_records(stub_iam, people):
    pk = submit_nodues(stub_iam, people)
    perms = (nodues_rules.VERIFY_PERMISSIONS["library"],)

    librarian = login(stub_iam, 6001, perms, people)
    rows = librarian.get(BASE + "nodues/pending/library/").json()["results"]
    assert pk in [row["id"] for row in rows]

    assert record(stub_iam, people, pk, "library",
                  nodues_rules.RESULT_CLEAR).status_code == 200

    librarian = login(stub_iam, 6001, perms, people)
    rows = librarian.get(BASE + "nodues/pending/library/").json()["results"]
    assert pk not in [row["id"] for row in rows]


# -- Assistantship helpers -----------------------------------------------------
def assign(stub_iam, users, student_id, thesis=None, ta_faculty=None, ta_course=""):
    """Record supervisor / TA assignments through the API as Department Admin 4001."""
    admin = login(stub_iam, 4001, ("oap.assignment.manage",), users)
    if thesis is not None:
        r = admin.post(
            BASE + "records/supervisor/",
            {"student_id": student_id, "faculty_id": thesis},
            format="json",
        )
        assert r.status_code == 201, r.content
    body = {"student_id": student_id}
    if ta_faculty is not None:
        body["faculty_id"] = ta_faculty
    if ta_course:
        body["course_code"] = ta_course
    if len(body) > 1:
        r = admin.post(BASE + "records/ta/", body, format="json")
        assert r.status_code == 201, r.content


def submit_claim(stub_iam, users, student_id=1003):
    c = login(stub_iam, student_id, STUDENT_CLAIM, users)
    return c.post(BASE + "assistantship/", {"claim_period": "2026-S1"},
                  format="json")


def ready_claim(stub_iam, users, student_id=1003, thesis=5001, ta=5002):
    """A claim submitted by a PG student with both supervisors assigned."""
    assign(stub_iam, users, student_id, thesis=thesis, ta_faculty=ta)
    r = submit_claim(stub_iam, users, student_id)
    assert r.status_code == 201, r.content
    return r.json()["id"]


def verify(stub_iam, users, pk, actor_id, role):
    c = login(stub_iam, actor_id, ("oap.assistantship.verify",), users)
    return c.post(f"{BASE}assistantship/{pk}/verify/", {"role": role},
                  format="json")


def both_verified(stub_iam, users, pk, thesis=5001, ta=5002):
    assert verify(stub_iam, users, pk, thesis,
                  assistantship_rules.ROLE_THESIS).status_code == 200
    r = verify(stub_iam, users, pk, ta, assistantship_rules.ROLE_TA)
    assert r.status_code == 200, r.content
    return r


def forward(stub_iam, users, pk, actor_id=4001):
    c = login(stub_iam, actor_id, ("oap.assistantship.review",), users)
    return c.post(f"{BASE}assistantship/{pk}/forward/", {}, format="json")


def hod_decide(stub_iam, users, pk, action, actor_id=2001):
    c = login(stub_iam, actor_id, ("oap.assistantship.decide",), users)
    return c.post(f"{BASE}assistantship/{pk}/decision/", {"action": action},
                  format="json")


def process_stipend(stub_iam, users, pk, actor_id=3001):
    c = login(stub_iam, actor_id, ("oap.assistantship.process_stipend",), users)
    return c.post(f"{BASE}assistantship/{pk}/stipend/", {}, format="json")


# -- Assistantship -------------------------------------------------------------
def test_pg_student_with_both_supervisors_submits_a_claim(stub_iam, people):
    assign(stub_iam, people, 1003, thesis=5001, ta_faculty=5002)

    r = submit_claim(stub_iam, people, 1003)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == assistantship_rules.INITIAL_STATE
    assert body["thesis_supervisor_id"] == 5001
    assert body["ta_supervisor_id"] == 5002


def test_ug_student_cannot_submit_a_claim(stub_iam, people):
    assert submit_claim(stub_iam, people, 1001).status_code == 400


def test_claim_with_only_a_course_only_ta_is_refused(stub_iam, people):
    assign(stub_iam, people, 1004, thesis=5001, ta_course="CS101")

    r = submit_claim(stub_iam, people, 1004)
    assert r.status_code == 400
    assert not AssistantshipClaim.objects.filter(student_id=1004).exists()


def test_thesis_then_ta_verification_reaches_department_review(stub_iam, people):
    pk = ready_claim(stub_iam, people)

    r = verify(stub_iam, people, pk, 5001, assistantship_rules.ROLE_THESIS)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_OTHER

    r = verify(stub_iam, people, pk, 5002, assistantship_rules.ROLE_TA)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_DEPARTMENT


def test_ta_then_thesis_verification_reaches_department_review(stub_iam, people):
    pk = ready_claim(stub_iam, people)

    r = verify(stub_iam, people, pk, 5002, assistantship_rules.ROLE_TA)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_OTHER

    r = verify(stub_iam, people, pk, 5001, assistantship_rules.ROLE_THESIS)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_DEPARTMENT


def test_one_faculty_in_both_roles_still_verifies_twice(stub_iam, people):
    """OA-BR-52: the two roles stay separate verifications."""
    pk = ready_claim(stub_iam, people, student_id=1005, thesis=5003, ta=5003)

    r = verify(stub_iam, people, pk, 5003, assistantship_rules.ROLE_THESIS)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_OTHER

    r = verify(stub_iam, people, pk, 5003, assistantship_rules.ROLE_TA)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_DEPARTMENT


def test_unassigned_faculty_cannot_verify(stub_iam, people):
    pk = ready_claim(stub_iam, people)
    for role in assistantship_rules.ROLES:
        assert verify(stub_iam, people, pk, 5009, role).status_code == 400


def test_the_same_role_cannot_verify_twice(stub_iam, people):
    pk = ready_claim(stub_iam, people)
    role = assistantship_rules.ROLE_THESIS
    assert verify(stub_iam, people, pk, 5001, role).status_code == 200
    assert verify(stub_iam, people, pk, 5001, role).status_code == 400


def test_hod_cannot_decide_before_the_department_forwards(stub_iam, people):
    pk = ready_claim(stub_iam, people)
    both_verified(stub_iam, people, pk)

    # Verified, but not forwarded yet (OA-BR-46: no step may be skipped).
    r = hod_decide(stub_iam, people, pk, "approve")
    assert r.status_code == 400


def test_full_approved_path(stub_iam, people):
    pk = ready_claim(stub_iam, people)
    both_verified(stub_iam, people, pk)

    r = forward(stub_iam, people, pk)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.AWAITING_HOD

    # The HoD of another department cannot see this claim at all.
    assert hod_decide(stub_iam, people, pk, "approve", actor_id=2002).status_code == 404

    r = hod_decide(stub_iam, people, pk, "approve")
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.APPROVED

    r = process_stipend(stub_iam, people, pk)
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.STIPEND_PROCESSED

    student = login(stub_iam, 1003, STUDENT_CLAIM, people)
    detail = student.get(f"{BASE}assistantship/{pk}/")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == assistantship_rules.STIPEND_PROCESSED
    assert [e["action"] for e in body["history"]] == [
        "submit",
        "verify_" + assistantship_rules.ROLE_THESIS,
        "verify_" + assistantship_rules.ROLE_TA,
        "forward",
        "approve",
        "process_stipend",
    ]
    assert {v["role"] for v in body["verifications"]} == set(
        assistantship_rules.ROLES
    )


def test_rejected_path_cannot_process_a_stipend(stub_iam, people):
    pk = ready_claim(stub_iam, people)
    both_verified(stub_iam, people, pk)
    assert forward(stub_iam, people, pk).status_code == 200

    r = hod_decide(stub_iam, people, pk, "reject")
    assert r.status_code == 200
    assert r.json()["status"] == assistantship_rules.REJECTED

    assert process_stipend(stub_iam, people, pk).status_code == 400


def test_student_sees_only_their_own_claims(stub_iam, people):
    mine = ready_claim(stub_iam, people, student_id=1003, thesis=5001, ta=5002)
    ready_claim(stub_iam, people, student_id=1005, thesis=5003, ta=5003)

    c = login(stub_iam, 1003, STUDENT_CLAIM, people)
    rows = c.get(BASE + "assistantship/").json()["results"]
    assert [row["id"] for row in rows] == [mine]
    assert all(row["student_id"] == 1003 for row in rows)
