"""Person A never sees person B's rows, by id, list, print or notification."""
import pytest

from modules.elm.tests.conftest import EMPLOYEE, FAC, FAC2, leave

pytestmark = pytest.mark.django_db


def test_foreign_request_is_absent(as_user, policy, calendar):
    pk = as_user(FAC, EMPLOYEE).post("/api/v1/elm/requests", leave("CL"),
                                     format="json").json()["id"]
    other = as_user(FAC2, EMPLOYEE)
    assert other.get("/api/v1/elm/requests").json()["results"] == []
    assert other.get(f"/api/v1/elm/requests/{pk}").status_code == 404
    assert other.get(f"/api/v1/elm/requests/{pk}/print").status_code == 404
    for action in ("withdraw", "cancel", "modify"):
        r = other.post(f"/api/v1/elm/requests/{pk}/{action}", leave("CL"), format="json")
        assert r.status_code == 404


def test_status_filter_cannot_widen_scope(as_user, policy, calendar):
    as_user(FAC, EMPLOYEE).post("/api/v1/elm/requests", leave("CL"), format="json")
    rows = as_user(FAC2, EMPLOYEE).get(
        "/api/v1/elm/requests?status=awaiting_unit_head").json()["results"]
    assert rows == []


def test_notifications_are_personal(as_user, policy, calendar):
    as_user(FAC, EMPLOYEE).post("/api/v1/elm/requests",
                                leave("CL", substitute_user_id=FAC2), format="json")
    assert as_user(FAC2, EMPLOYEE).get("/api/v1/elm/notifications").json()["results"]
    assert as_user(201, EMPLOYEE, kind="staff").get(
        "/api/v1/elm/notifications").json()["results"] == []
