"""Query budgets, so an N+1 fails a build instead of a page loading slowly.

The budget is per request rather than per row: each test adds rows and asserts
the count does not move with them.
"""
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.leave.domain import state_machine as sm
from modules.leave.tests.test_request_flow import apply_leave
from modules.leave.tests.test_schedule import BEAT_SCHEDULE  # noqa: F401

pytestmark = pytest.mark.django_db

BASE = "/api/v1/leave"


@pytest.fixture
def cohort(configured, employee):
    for uid in range(1001, 1006):
        apply_leave(employee(user_id=uid))
    return uid


@pytest.mark.parametrize(("path", "budget"), [
    (f"{BASE}/requests", 4),
    (f"{BASE}/balances", 40),
])
def test_a_list_endpoint_stays_within_its_budget(
        configured, employee, django_assert_max_num_queries, path, budget):
    apply_leave(employee())
    client = employee()
    with django_assert_max_num_queries(budget):
        assert client.get(path).status_code == 200


def test_the_request_count_does_not_grow_with_the_rows(configured, employee,
                                                       cohort):
    client = employee()
    with CaptureQueriesContext(connection) as first:
        client.get(f"{BASE}/requests")

    for uid in range(2001, 2011):
        apply_leave(employee(user_id=uid))

    with CaptureQueriesContext(connection) as second:
        client.get(f"{BASE}/requests")

    assert len(second) == len(first), (
        f"{len(first)} queries for 5 requests, {len(second)} for 15 - "
        f"a relation is being fetched per row")


def test_the_office_queue_does_not_grow_with_the_rows(configured, employee,
                                                      unit_head, cohort):
    client = unit_head()
    with CaptureQueriesContext(connection) as first:
        client.get(f"{BASE}/queue")

    for uid in range(3001, 3011):
        apply_leave(employee(user_id=uid))

    with CaptureQueriesContext(connection) as second:
        client.get(f"{BASE}/queue")

    assert len(second) == len(first)


def test_the_balances_read_is_bounded_by_the_categories_not_by_history(
        configured, employee):
    """Six categories, so six balances: history must not add queries."""
    from modules.leave.services import accounts as account_service

    account_service.open_year(user_id=1001, year=timezone.localdate().year,
                              is_faculty=False)
    client = employee()
    with CaptureQueriesContext(connection) as first:
        client.get(f"{BASE}/balances")

    for day in range(3):
        apply_leave(employee(), days=[timezone.localdate() + timedelta(days=20 + day)])

    with CaptureQueriesContext(connection) as second:
        client.get(f"{BASE}/balances")

    assert len(second) - len(first) <= 2


def test_the_transition_history_is_one_query_per_request(configured, employee):
    row = apply_leave(employee()).json()
    with CaptureQueriesContext(connection) as queries:
        response = employee().get(f"{BASE}/requests/{row['id']}/history")
    assert response.status_code == 200
    assert len(queries) <= 4
    assert sm.DRAFT in {t["from_status"] for t in response.json()["results"]}
