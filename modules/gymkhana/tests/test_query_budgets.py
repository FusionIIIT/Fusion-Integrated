"""Query counts for the list endpoints, so an N+1 fails a build.

The budget is per request, not per row: each test adds several rows and asserts
the count does not move with them.
"""
from datetime import timedelta

import pytest
from django.apps import apps
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana import registry
from modules.gymkhana.models import Club, PollChoice, PollTargetGroup, VotingPoll

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
STUDENT = tuple(registry.ROLE_GRANTS["student"])


def _client(stub_iam, *, user_id=2001):
    stub_iam(make_session(
        user_id=user_id,
        kind="student",
        roles=("student",),
        active_role="student",
        modules=("gymkhana",),
        permissions=STUDENT,
    ))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def _person(user_id, kind, *, batch_year=2024, discipline="CSE"):
    user_ref_cls = apps.get_model("directory", "UserRef")
    return user_ref_cls.objects.create(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def _make_club(n):
    return Club.objects.create(
        name=f"Club {n}",
        category="Technical",
        coordinator_user_id=2000 + n,
        co_coordinator_user_id=2100 + n,
        faculty_councillor_user_id=3000 + n,
        description=f"Club {n} details",
        status=Club.Status.CONFIRMED,
    )


def _make_poll(club, n):
    poll = VotingPoll.objects.create(
        club=club,
        title=f"Poll {n}",
        description=f"Description {n}",
        expires_at=timezone.now() + timedelta(days=2),
        created_by_user_id=club.coordinator_user_id,
        is_active=True,
    )
    PollChoice.objects.create(poll=poll, text=f"Choice A for {n}")
    PollChoice.objects.create(poll=poll, text=f"Choice B for {n}")
    PollTargetGroup.objects.create(poll=poll, batch_year=2024, discipline="CSE")
    return poll


def test_club_list_query_count_does_not_grow_with_rows(stub_iam):
    _person(2001, "student", batch_year=2024, discipline="CSE")
    client = _client(stub_iam, user_id=2001)

    for i in range(1, 4):
        _make_club(i)

    with CaptureQueriesContext(connection) as first:
        res = client.get(f"{ROOT}/clubs")
        assert res.status_code == 200

    for i in range(4, 8):
        _make_club(i)

    with CaptureQueriesContext(connection) as second:
        res = client.get(f"{ROOT}/clubs")
        assert res.status_code == 200

    assert len(second) == len(first), (
        f"{len(first)} queries for 3 clubs, {len(second)} for 7 — "
        "a relation is being fetched per row (N+1 query problem)"
    )


def test_poll_list_query_count_does_not_grow_with_rows(stub_iam):
    _person(2001, "student", batch_year=2024, discipline="CSE")
    client = _client(stub_iam, user_id=2001)
    club = _make_club(100)

    for i in range(1, 4):
        _make_poll(club, i)

    with CaptureQueriesContext(connection) as first:
        res = client.get(f"{ROOT}/polls")
        assert res.status_code == 200

    for i in range(4, 8):
        _make_poll(club, i)

    with CaptureQueriesContext(connection) as second:
        res = client.get(f"{ROOT}/polls")
        assert res.status_code == 200

    assert len(second) == len(first), (
        f"{len(first)} queries for 3 polls, {len(second)} for 7 — "
        "a relation is being fetched per row (N+1 query problem)"
    )
