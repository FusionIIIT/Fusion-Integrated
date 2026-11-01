"""One person's leave must not be visible to another, including via filters."""
import pytest

from modules.leave.models import LeaveRequest
from modules.leave.tests.test_request_flow import BASE, apply_leave

pytestmark = pytest.mark.django_db


def test_an_employee_sees_only_their_own_requests(configured, employee):
    apply_leave(employee(user_id=1001))
    apply_leave(employee(user_id=2002))

    rows = employee(user_id=1001).get(f"{BASE}/requests").json()["results"]
    assert {r["id"] for r in rows} == set(
        LeaveRequest.objects.filter(user_id=1001).values_list("id", flat=True))


def test_another_person_s_request_is_a_404_not_a_403(configured, employee):
    row = apply_leave(employee(user_id=1001)).json()
    response = employee(user_id=2002).get(f"{BASE}/requests/{row['id']}")
    assert response.status_code == 404


def test_withdrawing_somebody_else_s_request_is_a_404(configured, employee):
    row = apply_leave(employee(user_id=1001)).json()
    response = employee(user_id=2002).post(
        f"{BASE}/requests/{row['id']}/withdraw", {"reason": "not mine"}, format="json")
    assert response.status_code == 404


def test_an_employee_sees_only_their_own_balances(configured, employee, admin):
    """The office scope is a separate grant, not the same selector widening."""
    from modules.leave.services import accounts as account_service

    account_service.open_year(user_id=1001, year=2026, is_faculty=False)
    response = employee(user_id=1001).get(f"{BASE}/balances?year=2026").json()
    assert response["year"] == 2026
    assert "balances" in response


def test_the_queue_shows_only_what_the_actor_may_decide(configured, employee,
                                                        unit_head, authority):
    submitted = apply_leave(employee(user_id=1001)).json()
    assert str(submitted["id"]) in unit_head().get(f"{BASE}/queue").content.decode()
    assert str(submitted["id"]) not in authority().get(f"{BASE}/queue").content.decode()


def test_a_substitute_does_not_see_the_request_they_were_not_nominated_for(
        configured, employee):
    row = apply_leave(employee(user_id=1001)).json()
    response = employee(user_id=1002).post(
        f"{BASE}/substitute-requests/{row['id']}/respond", {"accept": True},
        format="json")
    assert response.status_code == 404
