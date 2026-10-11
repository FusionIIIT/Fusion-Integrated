"""Every endpoint, probed by a principal who should not reach it (Step 5.5).

The fake IAM hands out whatever permission set a test asks for, so the tests
that matter are the refusals: the same request with one permission fewer.
"""
import pytest

from modules.elm.models import LeaveApplication
from modules.elm.services import applications as service
from modules.elm.tests.support import APPROVER_PERMS, EMPLOYEE_PERMS, principal

pytestmark = pytest.mark.django_db

BASE = "/api/v1/elm"
OTHER = 9009
APPROVER_ID = 2002


def owner():
    """The plain employee the owning application belongs to (Step 5.2)."""
    return principal(user_id=OTHER)


def approver_session(**kw):
    return {"user_id": APPROVER_ID, "permissions": APPROVER_PERMS,
            "kind": "faculty", "roles": ("Leave Approver",),
            "active_role": "Leave Approver", "modules": ("elm",), **kw}


def employee_session(**kw):
    return {"user_id": 1001, "permissions": EMPLOYEE_PERMS,
            "modules": ("elm",), **kw}


def make_application(leave_type, next_monday, user_id):
    return LeaveApplication.objects.create(
        user_id=user_id, leave_type=leave_type, start_date=next_monday,
        end_date=next_monday, days=1)


class TestTheModuleGate:

    def test_an_unauthenticated_caller_gets_401(self, anon_client):
        assert anon_client.get(f"{BASE}/applications").status_code == 401

    def test_a_caller_without_the_module_grant_gets_403(self, api):
        client = api(**employee_session(modules=()))
        response = client.get(f"{BASE}/applications")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"


class TestThePermissionGate:

    def test_a_foreign_row_is_404_before_it_is_403(self, api, make_type,
                                                   next_monday):
        # A row the caller cannot see must not be confirmable by its status
        # code: the refusal is "not found", not "you may not".
        application = make_application(make_type(), next_monday, OTHER)
        client = api(**employee_session())
        response = client.post(f"{BASE}/applications/{application.pk}/transition",
                               {"to_status": "approved"}, format="json")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_an_employee_cannot_approve_their_own_request(self, api, make_type,
                                                          next_monday):
        application = make_application(make_type(), next_monday, 1001)
        client = api(**employee_session())
        response = client.post(f"{BASE}/applications/{application.pk}/transition",
                               {"to_status": "approved"}, format="json")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "actor_not_allowed"

    def test_a_caller_without_apply_cannot_submit(self, api, make_type,
                                                  next_monday):
        leave_type = make_type()
        client = api(user_id=1001, permissions=("elm.application.view",))
        response = client.post(f"{BASE}/applications/submit", {
            "leave_type_id": leave_type.pk, "start_date": str(next_monday),
            "end_date": str(next_monday)}, format="json")
        assert response.status_code == 403

    def test_an_approver_cannot_configure_leave_types(self, api):
        client = api(**approver_session())
        response = client.post(f"{BASE}/types/create",
                               {"code": "SL", "name": "Special Leave"},
                               format="json")
        assert response.status_code == 403

    def test_an_approver_cannot_add_holidays(self, api):
        client = api(**approver_session())
        response = client.post(f"{BASE}/holidays/create",
                               {"date": "2026-12-25", "name": "Christmas"},
                               format="json")
        assert response.status_code == 403

    def test_an_approver_cannot_grant_balances(self, api, make_type):
        leave_type = make_type()
        client = api(**approver_session())
        response = client.post(f"{BASE}/balances/grant", {
            "user_id": 1001, "leave_type_id": leave_type.pk, "year": 2026,
            "days": "1.0", "note": "Overtime"}, format="json")
        assert response.status_code == 403


class TestScoping:

    def test_an_employee_lists_only_their_own_requests(self, api, make_type,
                                                       next_monday):
        leave_type = make_type()
        mine = make_application(leave_type, next_monday, 1001)
        make_application(leave_type, next_monday, OTHER)
        client = api(**employee_session())
        rows = client.get(f"{BASE}/applications").json()["results"]
        assert [row["id"] for row in rows] == [mine.pk]

    def test_a_foreign_request_is_404_not_403(self, api, make_type, next_monday):
        theirs = make_application(make_type(), next_monday, OTHER)
        client = api(**employee_session())
        foreign = client.get(f"{BASE}/applications/{theirs.pk}")
        missing = client.get(f"{BASE}/applications/999999")
        assert foreign.status_code == 404
        assert missing.status_code == 404

    def test_a_foreign_history_is_404(self, api, make_type, next_monday):
        theirs = make_application(make_type(), next_monday, OTHER)
        client = api(**employee_session())
        assert client.get(f"{BASE}/applications/{theirs.pk}/history").status_code == 404

    def test_the_inbox_never_contains_the_approvers_own_request(self, api,
                                                                make_type,
                                                                next_monday):
        leave_type = make_type()
        own = make_application(leave_type, next_monday, APPROVER_ID)
        other = make_application(leave_type, next_monday, OTHER)
        client = api(**approver_session())
        rows = client.get(f"{BASE}/approvals").json()["results"]
        ids = [row["id"] for row in rows]
        assert other.pk in ids
        assert own.pk not in ids

    def test_an_employee_asking_for_a_foreign_balance_reads_their_own(self, api,
                                                                     make_type):
        make_type()
        client = api(**employee_session())
        response = client.get(f"{BASE}/balances", {"user_id": OTHER, "year": 2026})
        assert response.status_code == 200
        assert {row["user_id"] for row in response.json()} == {1001}


class TestHostileInput:

    def test_an_unparseable_year_is_a_400(self, api):
        client = api(**employee_session())
        response = client.get(f"{BASE}/balances", {"year": "abc"})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_filter"

    def test_an_unknown_target_status_is_refused(self, api, make_type,
                                                 next_monday):
        application = make_application(make_type(), next_monday, 1001)
        client = api(**employee_session())
        response = client.post(f"{BASE}/applications/{application.pk}/transition",
                               {"to_status": "vanished"}, format="json")
        assert response.status_code == 400


class TestTheHappyPathThroughHTTP:

    def test_an_employee_submits_and_sees_it_in_their_list(self, api, make_type,
                                                           next_monday):
        leave_type = make_type()
        client = api(**employee_session())
        created = client.post(f"{BASE}/applications/submit", {
            "leave_type_id": leave_type.pk, "start_date": str(next_monday),
            "end_date": str(next_monday), "reason": "Personal work"},
            format="json")
        assert created.status_code == 201
        assert created.json()["status"] == "pending"
        assert "withdrawn" in created.json()["allowed_transitions"]

        rows = client.get(f"{BASE}/applications").json()["results"]
        assert [row["id"] for row in rows] == [created.json()["id"]]

    def test_an_approver_decides_through_http(self, api, make_type, next_monday):
        # Submitted through the service, so the annual grant exists and the
        # balance guard has something to compare against.
        leave_type = make_type()
        application = service.submit_application(
            actor=owner(), leave_type_id=leave_type.pk, start_date=next_monday,
            end_date=next_monday, reason="Personal work")
        client = api(**approver_session())
        response = client.post(f"{BASE}/applications/{application.pk}/transition",
                               {"to_status": "approved", "note": "Approved"},
                               format="json")
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        assert response.json()["allowed_transitions"] == []

    def test_an_administrator_creates_a_type_version(self, api):
        client = api(user_id=3003,
                     permissions=(*APPROVER_PERMS, "elm.balance.manage",
                                  "elm.policy.manage"), modules=("elm",),
                     kind="staff", roles=("Leave Administrator",),
                     active_role="Leave Administrator")
        response = client.post(f"{BASE}/types/create", {
            "code": "SL", "name": "Special Leave",
            "annual_entitlement_days": "5.0"}, format="json")
        assert response.status_code == 201
        assert response.json()["code"] == "SL"
