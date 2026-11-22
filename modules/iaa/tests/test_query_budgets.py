"""Query counts for the list endpoints, so an N+1 fails a build.

Each test measures the same request at 2 rows and again at 20 and asserts the two counts are
equal, with a ceiling as well: a ceiling measured at one size hides an N+1.
"""
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.iaa.domain import roles
from modules.iaa.services import anomalies, configuration, observations, review
from modules.iaa.tests.helpers import FACULTY, api_client, new_expense

pytestmark = pytest.mark.django_db

B = "/api/v1/iaa"
SMALL, LARGE = 2, 20


def counted(client, path) -> int:
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"{B}{path}")
    assert response.status_code == 200, response.content
    return len(queries)


def same_count_at_both_sizes(stub_iam, who, path, grow, *, ceiling):
    """`grow(n)` adds n rows the endpoint lists; the request must not cost more for them."""
    grow(SMALL)
    client = api_client(stub_iam, *who)
    counted(client, path)                                              # warm up caches
    first = counted(client, path)
    grow(LARGE - SMALL)
    second = counted(client, path)
    assert first == second, f"{first} queries at {SMALL} rows, {second} at {LARGE}: an N+1"
    assert second <= ceiling, f"{second} queries; the budget is {ceiling}"


def test_my_requests_list_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    same_count_at_both_sizes(
        stub_iam, (101, FACULTY), "/records",
        lambda n: [new_expense(people.creator) for _ in range(n)], ceiling=8)


def test_the_finance_queue_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    same_count_at_both_sizes(
        stub_iam, (201, roles.FINANCE), "/records?status=submitted",
        lambda n: [new_expense(people.creator) for _ in range(n)], ceiling=8)


def test_an_approvers_queue_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    def grow(n):
        for _ in range(n):
            review.validate(people.finance, new_expense(people.creator).pk)
    same_count_at_both_sizes(stub_iam, (301, roles.HOD), "/records", grow, ceiling=8)


def test_the_anomaly_list_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    same_count_at_both_sizes(
        stub_iam, (201, roles.FINANCE), "/anomalies",
        lambda n: [anomalies.flag(people.finance, category="policy", description="x")
                   for _ in range(n)], ceiling=6)


def test_the_observation_list_costs_the_same_at_two_rows_and_twenty(
        stub_iam, people, configured):
    rec = new_expense(people.creator)
    same_count_at_both_sizes(
        stub_iam, (401, roles.AUDITOR), "/observations",
        lambda n: [observations.raise_observation(people.auditor, title="t", detail="d",
                                                  record_id=rec.pk) for _ in range(n)],
        ceiling=8)


def test_the_notification_feed_costs_the_same_at_two_rows_and_twenty(
        stub_iam, people, configured):
    same_count_at_both_sizes(
        stub_iam, (101, FACULTY), "/notifications",
        lambda n: [new_expense(people.creator) for _ in range(n)], ceiling=8)


def test_the_budget_ledger_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    def grow(n):
        for _ in range(n):
            configuration.add_budget_entry(people.admin, financial_year_id=configured.pk,
                                           department="CSE", kind="allocation",
                                           amount=Decimal("1000"))
    same_count_at_both_sizes(
        stub_iam, (501, roles.SYSTEM_ADMIN), f"/config/budget-entries?financial_year_id={configured.pk}",
        grow, ceiling=6)


def test_the_report_costs_the_same_at_two_rows_and_twenty(stub_iam, people, configured):
    same_count_at_both_sizes(
        stub_iam, (201, roles.FINANCE), "/reports/summary",
        lambda n: [new_expense(people.creator) for _ in range(n)], ceiling=10)
