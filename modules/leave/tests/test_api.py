"""The two gates, and the scope behind them.

The permission decides whether an endpoint answers at all; the queryset decides
what it answers with. Both are tested here, because a correct permission over a
queryset that was never narrowed is the failure that looks like working
software.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest, SubstituteNomination
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db

EMPLOYEE = 501
COLLEAGUE = 502
HEAD_CSE = 601
HEAD_ECE = 602
REGISTRAR = 701
ADMIN = 900

EMPLOYEE_PERMS = (
    "leave.request.create", "leave.request.view_self", "leave.request.withdraw",
    "leave.substitute.respond",
)


@pytest.fixture
def people():
    for uid, dept in (
        (EMPLOYEE, "CSE"), (COLLEAGUE, "ECE"), (HEAD_CSE, "CSE"),
        (HEAD_ECE, "ECE"), (REGISTRAR, "Administration"), (ADMIN, "Administration"),
    ):
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
            kind="faculty", department=dept,
        )


def client(stub_iam, user_id, permissions, kind="faculty"):
    stub_iam(make_session(
        user_id=user_id, kind=kind, modules=("leave",), permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def make_request(user_id, unit, state=State.AWAITING_UNIT_HEAD, **kw):
    return LeaveRequest.objects.create(
        user_id=user_id, category=Category.CL.value, state=state.value,
        starts_on="2026-03-02", ends_on="2026-03-03", reason="Personal",
        requested_days=2, unit=unit, **kw,
    )


class TestTheModuleGate:
    def test_without_the_module_grant_nothing_answers(self, stub_iam, people):
        stub_iam(make_session(user_id=EMPLOYEE, modules=(), permissions=EMPLOYEE_PERMS))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        assert c.get("/api/v1/leave/me/requests").status_code == 403

    def test_the_module_grant_alone_is_not_enough(self, stub_iam, people):
        c = client(stub_iam, HEAD_CSE, ("leave.request.view_self",))
        assert c.get("/api/v1/leave/review").status_code == 403


class TestSelfService:
    def test_you_see_your_own_requests_and_nobody_elses(self, stub_iam, people):
        make_request(EMPLOYEE, "CSE")
        make_request(COLLEAGUE, "ECE")

        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)
        rows = c.get("/api/v1/leave/me/requests").json()

        assert [r["user_id"] for r in rows] == [EMPLOYEE]

    def test_somebody_elses_request_is_not_found_rather_than_refused(
        self, stub_iam, people
    ):
        theirs = make_request(COLLEAGUE, "ECE")
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        # 404, not 403: a refusal would confirm the request exists.
        assert c.get(f"/api/v1/leave/requests/{theirs.pk}").status_code == 404

    def test_you_cannot_withdraw_a_request_that_is_not_yours(self, stub_iam, people):
        theirs = make_request(COLLEAGUE, "ECE")
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        assert c.post(f"/api/v1/leave/requests/{theirs.pk}/withdraw").status_code == 404

    def test_applying_takes_the_employee_from_the_credential(self, stub_iam, people):
        factories.setup_all(EMPLOYEE)
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        body = c.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": "2026-03-02", "ends_on": "2026-03-03",
            "reason": "Personal work", "user_id": COLLEAGUE,
        }, format="json")

        assert body.status_code == 201
        # The user_id in the body is ignored; leave is applied for by the applicant.
        assert body.json()["user_id"] == EMPLOYEE

    def test_the_unit_comes_from_the_directory_not_the_request(self, stub_iam, people):
        factories.setup_all(EMPLOYEE)
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        created = c.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": "2026-03-02", "ends_on": "2026-03-03",
            "reason": "Personal work", "unit": "ECE",
        }, format="json").json()

        assert LeaveRequest.objects.get(pk=created["id"]).unit == "CSE"


class TestReviewIsScopedToTheUnit:
    def test_a_head_sees_only_their_own_unit(self, stub_iam, people):
        make_request(EMPLOYEE, "CSE")
        make_request(COLLEAGUE, "ECE")

        c = client(stub_iam, HEAD_CSE, ("leave.request.review", "leave.balance.view"))
        rows = c.get("/api/v1/leave/review").json()

        assert [r["user_id"] for r in rows] == [EMPLOYEE]

    def test_a_head_cannot_open_another_units_request(self, stub_iam, people):
        theirs = make_request(COLLEAGUE, "ECE")
        c = client(stub_iam, HEAD_CSE, ("leave.request.review", "leave.balance.view"))

        assert c.get(f"/api/v1/leave/requests/{theirs.pk}").status_code == 404

    def test_a_head_cannot_decide_another_units_request(self, stub_iam, people):
        theirs = make_request(COLLEAGUE, "ECE")
        c = client(stub_iam, HEAD_CSE, ("leave.request.review",))

        response = c.post(
            f"/api/v1/leave/review/{theirs.pk}", {"approve": True}, format="json")

        assert response.status_code == 404

    def test_the_establishment_does_see_the_whole_institute(self, stub_iam, people):
        make_request(EMPLOYEE, "CSE", state=State.AWAITING_ESTABLISHMENT)
        make_request(COLLEAGUE, "ECE", state=State.AWAITING_ESTABLISHMENT)

        c = client(stub_iam, REGISTRAR, ("leave.request.route",))
        rows = c.get("/api/v1/leave/routing").json()

        assert sorted(r["user_id"] for r in rows) == [EMPLOYEE, COLLEAGUE]


class TestSubstitute:
    def test_you_only_see_nominations_addressed_to_you(self, stub_iam, people):
        mine = make_request(EMPLOYEE, "CSE", state=State.AWAITING_SUBSTITUTE)
        theirs = make_request(EMPLOYEE, "CSE", state=State.AWAITING_SUBSTITUTE)
        SubstituteNomination.objects.create(request=mine, substitute_user_id=COLLEAGUE)
        SubstituteNomination.objects.create(request=theirs, substitute_user_id=HEAD_CSE)

        c = client(stub_iam, COLLEAGUE, EMPLOYEE_PERMS)
        rows = c.get("/api/v1/leave/nominations").json()

        assert [r["id"] for r in rows] == [mine.pk]

    def test_you_cannot_answer_a_nomination_addressed_to_somebody_else(
        self, stub_iam, people
    ):
        theirs = make_request(EMPLOYEE, "CSE", state=State.AWAITING_SUBSTITUTE)
        SubstituteNomination.objects.create(request=theirs, substitute_user_id=HEAD_CSE)

        c = client(stub_iam, COLLEAGUE, EMPLOYEE_PERMS)
        response = c.post(
            f"/api/v1/leave/nominations/{theirs.pk}/respond",
            {"accepted": True}, format="json")

        assert response.status_code == 404


class TestAdministration:
    def test_policy_maintenance_needs_its_own_permission(self, stub_iam, people):
        c = client(stub_iam, REGISTRAR, ("leave.request.sanction",))
        assert c.get("/api/v1/leave/admin/policies").status_code == 403

    def test_an_administrator_can_read_the_policy(self, stub_iam, people):
        factories.make_policy()
        c = client(stub_iam, ADMIN, ("leave.policy.manage",))

        rows = c.get("/api/v1/leave/admin/policies").json()

        assert [r["version"] for r in rows] == ["2026.1"]

    def test_offline_recording_needs_its_own_permission(self, stub_iam, people):
        c = client(stub_iam, ADMIN, ("leave.policy.manage",))
        response = c.post("/api/v1/leave/admin/offline", {
            "user_id": EMPLOYEE, "category": "CL", "starts_on": "2026-03-02",
            "ends_on": "2026-03-02", "reason": "On file",
        }, format="json")
        assert response.status_code == 403

    def test_an_offline_entry_names_the_administrator_from_the_credential(
        self, stub_iam, people
    ):
        factories.setup_all(EMPLOYEE)
        c = client(stub_iam, ADMIN, ("leave.offline.record",))

        created = c.post("/api/v1/leave/admin/offline", {
            "user_id": EMPLOYEE, "category": "CL", "starts_on": "2026-03-02",
            "ends_on": "2026-03-02", "reason": "Sanction letter 44/2026",
        }, format="json")

        assert created.status_code == 201
        entry = LeaveRequest.objects.get(pk=created.json()["id"])
        assert entry.state == State.CLOSED.value
        assert entry.transitions.get().actor_user_id == ADMIN


class TestErrorsAreShapedCorrectly:
    def test_an_illegal_transition_is_409_not_500(self, stub_iam, people):
        closed = make_request(EMPLOYEE, "CSE", state=State.CLOSED)
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        response = c.post(f"/api/v1/leave/requests/{closed.pk}/withdraw")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "request_closed"

    def test_a_rejected_application_explains_itself(self, stub_iam, people):
        factories.setup_all(EMPLOYEE)
        c = client(stub_iam, EMPLOYEE, EMPLOYEE_PERMS)

        response = c.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": "2026-03-04", "ends_on": "2026-03-02",
            "reason": "Personal work",
        }, format="json")

        assert response.status_code == 400
        assert "before it starts" in response.json()["error"]["message"]
