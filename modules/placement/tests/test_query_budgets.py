"""Query counts for the list endpoints, so an N+1 fails a build."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import (
    Announcement,
    Application,
    Company,
    JobPosting,
    Offer,
)

pytestmark = pytest.mark.django_db

STAFF = ("placement.job_posting.view", "placement.application.view",
         "placement.company.manage", "placement.offer.create",
         "placement.announcement.publish")


def _client(stub_iam, permissions=STAFF, uid=9, kind="staff"):
    stub_iam(make_session(user_id=uid, kind=kind, permissions=permissions,
                          modules=("placement",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _company(n):
    return Company.objects.create(
        name=f"Co{n}", slug=f"co{n}", status="active",
        approval_status="approved", approved_by_user_id=9)


def _posting(company, n):
    return JobPosting.objects.create(
        company=company, placement_year="2026-27", title=f"Role {n}",
        description="Build things.", status="published",
        closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={"gte": ["cpi", 7.0]},
        eligibility_rule_locked_at=timezone.now())


@pytest.fixture
def cohort():
    """Five postings across five companies, each with an application and offer."""
    out = []
    for n in range(5):
        company = _company(n)
        posting = _posting(company, n)
        application = Application.objects.create(
            posting=posting, user_id=1000 + n, status="selected",
            cpi_at_apply="8.00")
        Offer.objects.create(posting=posting, application=application,
                             user_id=1000 + n, ctc_lpa="12.00", status="issued",
                             respond_by=timezone.now() + timedelta(days=3))
        Announcement.objects.create(title=f"Notice {n}", body="text",
                                    placement_year="2026-27",
                                    published_by_user_id=9)
        out.append(posting)
    return out


@pytest.mark.parametrize(("path", "budget"), [
    ("/api/v1/placement/postings", 2),
    ("/api/v1/placement/applications", 4),
    ("/api/v1/placement/companies", 7),
    ("/api/v1/placement/offers", 2),
    ("/api/v1/placement/announcements", 2),
])
def test_a_list_endpoint_stays_within_its_budget(
        stub_iam, cohort, django_assert_max_num_queries, path, budget):
    client = _client(stub_iam)
    with django_assert_max_num_queries(budget):
        assert client.get(path).status_code == 200


def test_the_count_does_not_grow_with_the_rows(stub_iam, cohort,
                                               django_assert_num_queries):
    """The property that matters: five more postings, same number of queries."""
    client = _client(stub_iam)

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as first:
        client.get("/api/v1/placement/postings")

    for n in range(5, 10):
        _posting(_company(n), n)

    with CaptureQueriesContext(connection) as second:
        client.get("/api/v1/placement/postings")

    assert len(second) == len(first), (
        f"{len(first)} queries for 5 postings, {len(second)} for 10 — "
        f"a relation is being fetched per row")
