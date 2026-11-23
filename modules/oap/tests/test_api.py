import datetime as dt

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.oap import registry
from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    NoDuesCase,
    Notification,
    TAAssignment,
    ThesisSupervisorAssignment,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/oap"


class Actor:
    """One signed-in person. The IAM fake holds a single session, so each call
    re-installs this person's session before it runs."""

    def __init__(self, stub_iam, uid, roles, active, kind):
        self.stub_iam, self.uid, self.roles, self.active, self.kind = (
            stub_iam,
            uid,
            roles,
            active,
            kind,
        )
        self.perms = {c for r in roles for c in registry.ROLE_GRANTS.get(r, [])}
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token abc")

    def _install(self):
        self.stub_iam(
            make_session(
                user_id=self.uid,
                kind=self.kind,
                modules=("oap",),
                permissions=self.perms,
                roles=tuple(self.roles),
                active_role=self.active,
            )
        )

    def get(self, url, **kw):
        self._install()
        return self.client.get(url, **kw)

    def post(self, url, data=None, **kw):
        self._install()
        return self.client.post(url, data, **kw)


def login(stub_iam, uid, roles, active, kind="student"):
    return Actor(stub_iam, uid, roles, active, kind)


def rows(resp):
    body = resp.json()
    return body["results"] if isinstance(body, dict) else body


def test_student_submits_and_sees_only_own_leave(stub_iam):
    a = login(stub_iam, 1001, ["student"], "student")
    r = a.post(
        f"{BASE}/leave-applications",
        {"reason": "Fever", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert r.status_code == 201
    b = login(stub_iam, 2002, ["student"], "student")
    assert rows(b.get(f"{BASE}/leave-applications")) == []
    mine = rows(a.get(f"{BASE}/leave-applications"))
    assert [x["id"] for x in mine] == [r.json()["id"]]


def test_other_students_leave_is_404_not_403(stub_iam):
    owner = login(stub_iam, 1001, ["student"], "student")
    lid = owner.post(
        f"{BASE}/leave-applications",
        {"reason": "x", "from_date": "2026-12-01", "to_date": "2026-12-01"},
        format="json",
    ).json()["id"]
    other = login(stub_iam, 2002, ["student"], "student")
    assert other.get(f"{BASE}/leave-applications/{lid}").status_code == 404


def test_leave_rejects_inverted_dates(stub_iam):
    a = login(stub_iam, 1001, ["student"], "student")
    r = a.post(
        f"{BASE}/leave-applications",
        {"reason": "x", "from_date": "2026-12-05", "to_date": "2026-12-01"},
        format="json",
    )
    assert r.status_code == 400


def test_module_grant_and_permission_are_separate_gates(stub_iam):
    stub_iam(make_session(user_id=3003, modules=(), permissions={"oap.leave_application.create"}))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    r = c.post(f"{BASE}/leave-applications", {}, format="json")
    assert r.status_code == 403


def test_permission_without_module_grant_is_refused(stub_iam):
    stub_iam(
        make_session(
            user_id=3003, modules=("placement_cell",), permissions={"oap.leave_application.create"}
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert c.post(f"{BASE}/leave-applications", {}, format="json").status_code == 403


def test_student_cannot_decide_leave_even_when_holding_the_permission(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    lid = s.post(
        f"{BASE}/leave-applications",
        {"reason": "x", "from_date": "2026-12-01", "to_date": "2026-12-01"},
        format="json",
    ).json()["id"]
    sneaky = login(stub_iam, 1001, ["student", "Head of Department"], "student")
    assert (
        sneaky.post(
            f"{BASE}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json"
        ).status_code
        == 403
    )


def test_hod_decides_leave_and_student_is_notified(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    lid = s.post(
        f"{BASE}/leave-applications",
        {"reason": "x", "from_date": "2026-12-01", "to_date": "2026-12-01"},
        format="json",
    ).json()["id"]
    hod = login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE}/leave-applications/{lid}/decision", {"outcome": "reject"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert LeaveApplication.objects.get(pk=lid).decided_by_user_id == 9001
    assert Notification.objects.filter(
        recipient_user_id=1001, channel="email", status="pending"
    ).exists()


def test_two_designations_show_only_the_acting_role(stub_iam):
    # Holds HoD and student together; acting as student must not see the HoD queue.
    s = login(stub_iam, 1001, ["student"], "student")
    s.post(
        f"{BASE}/leave-applications",
        {"reason": "x", "from_date": "2026-12-01", "to_date": "2026-12-01"},
        format="json",
    )
    as_student = login(stub_iam, 1001, ["student", "Head of Department"], "student")
    assert len(rows(as_student.get(f"{BASE}/leave-applications"))) == 1
    as_hod = login(stub_iam, 1001, ["student", "Head of Department"], "Head of Department")
    assert len(rows(as_hod.get(f"{BASE}/leave-applications"))) == 1


def test_bonafide_decision_needs_verification_first(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    bid = s.post(f"{BASE}/bonafide-requests", {"purpose": "bank"}, format="json").json()["id"]
    aa = login(stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff")
    assert (
        aa.post(
            f"{BASE}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json"
        ).status_code
        == 409
    )
    assert aa.post(f"{BASE}/bonafide-requests/{bid}/verify").status_code == 200
    assert (
        aa.post(
            f"{BASE}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json"
        ).status_code
        == 200
    )
    assert s.get(f"{BASE}/bonafide-requests/{bid}/certificate").status_code == 200
    assert BonafideRequest.objects.get(pk=bid).status == "approved"


def test_certificate_is_refused_before_approval(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    bid = s.post(f"{BASE}/bonafide-requests", {"purpose": ""}, format="json").json()["id"]
    assert s.get(f"{BASE}/bonafide-requests/{bid}/certificate").status_code == 409


def test_no_dues_cannot_finalize_while_authorities_are_pending(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    assert s.post(f"{BASE}/no-dues-cases").status_code == 201
    assert s.post(f"{BASE}/no-dues-cases").status_code == 409
    aa = login(stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff")
    cid = NoDuesCase.objects.get(user_id=1001).pk
    assert aa.post(f"{BASE}/no-dues-cases/{cid}/finalize").status_code == 409
    assert not NoDuesCase.objects.get(pk=cid).finalized


def test_librarian_records_only_the_library_domain(stub_iam):
    s = login(stub_iam, 1001, ["student"], "student")
    s.post(f"{BASE}/no-dues-cases")
    cid = NoDuesCase.objects.get(user_id=1001).pk
    lib = login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE}/no-dues-cases/{cid}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"] == {"library": "clear"}
    hostel = login(stub_iam, 7002, ["Hostel Warden"], "Hostel Warden", kind="staff")
    assert hostel.get(f"{BASE}/no-dues-cases/{cid}").json()["results"] == {"hostel": "pending"}


def test_claim_needs_both_supervisors_assigned(stub_iam):
    s = login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = s.post(f"{BASE}/assistantship-claims")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "supervisor_unresolved"


def _assign(stub_iam, student, thesis, ta):
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    assert (
        da.post(
            f"{BASE}/thesis-supervisor-assignments",
            {"student_user_id": student, "supervisor_user_id": thesis},
            format="json",
        ).status_code
        == 201
    )
    assert (
        da.post(
            f"{BASE}/ta-assignments",
            {"student_user_id": student, "course_code": "CS101", "supervisor_user_id": ta},
            format="json",
        ).status_code
        == 201
    )
    return da


def test_full_assistantship_path_with_one_faculty_in_both_roles(stub_iam):
    _assign(stub_iam, 1001, 5001, 5001)
    pg = login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE}/assistantship-claims").json()["id"]
    fac = login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    assert (
        fac.post(
            f"{BASE}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json"
        ).json()["status"]
        == "awaiting_other_verification"
    )
    assert (
        fac.post(
            f"{BASE}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json"
        ).json()["status"]
        == "awaiting_department_review"
    )
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    assert (
        da.post(f"{BASE}/assistantship-claims/{cid}/forward").json()["status"]
        == "awaiting_hod_decision"
    )
    hod = login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    assert (
        hod.post(
            f"{BASE}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json"
        ).json()["status"]
        == "approved_awaiting_stipend"
    )
    aa = login(stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff")
    assert (
        aa.post(f"{BASE}/assistantship-claims/{cid}/stipend").json()["status"]
        == "stipend_processed"
    )


def test_supervisor_cannot_verify_a_claim_they_are_not_assigned_to(stub_iam):
    _assign(stub_iam, 1001, 5001, 5002)
    pg = login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE}/assistantship-claims").json()["id"]
    stranger = login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    r = stranger.post(
        f"{BASE}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json"
    )
    assert r.status_code == 403
    assert AssistantshipClaim.objects.get(pk=cid).status == "awaiting_dual_verification"


def test_department_cannot_forward_before_both_verifications(stub_iam):
    _assign(stub_iam, 1001, 5001, 5002)
    pg = login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE}/assistantship-claims").json()["id"]
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    assert da.post(f"{BASE}/assistantship-claims/{cid}/forward").status_code == 409


def test_thesis_supervisor_reassignment_supersedes_the_old_row(stub_iam):
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    for sup in (5001, 5003):
        assert (
            da.post(
                f"{BASE}/thesis-supervisor-assignments",
                {"student_user_id": 1001, "supervisor_user_id": sup},
                format="json",
            ).status_code
            == 201
        )
    current = ThesisSupervisorAssignment.objects.filter(student_user_id=1001, superseded_at=None)
    assert [t.supervisor_user_id for t in current] == [5003]


def test_ta_assignment_needs_course_or_faculty(stub_iam):
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE}/ta-assignments",
        {"student_user_id": 1001, "course_code": "", "supervisor_user_id": None},
        format="json",
    )
    assert r.status_code == 400
    assert TAAssignment.objects.count() == 0


def test_seminar_is_requested_scheduled_and_visible_to_faculty(stub_iam):
    pg = login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE}/seminar-requests").json()["id"]
    da = login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r = da.post(
        f"{BASE}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Seminar Hall"},
        format="json",
    )
    assert r.status_code == 201
    fac = login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    assert len(rows(fac.get(f"{BASE}/seminar-schedules"))) == 1
    assert (
        da.post(
            f"{BASE}/seminar-requests/{sid}/schedule",
            {"scheduled_for": when, "venue": "Hall"},
            format="json",
        ).status_code
        == 409
    )


def test_student_cannot_see_seminar_schedules_without_the_permission(stub_iam):
    stub_iam(
        make_session(user_id=1001, modules=("oap",), permissions={"oap.leave_application.create"})
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert c.get(f"{BASE}/seminar-schedules").status_code == 403


def test_reminders_stay_silent_without_a_policy():
    from modules.oap.services import reminders

    assert reminders.send_due_reminders()["sent"] == 0
