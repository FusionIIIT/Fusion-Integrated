"""List endpoints cost the same queries for three rows as for one, so an N+1 fails the build."""
from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.leave.services import applications
from modules.leave.tests.conftest import FACULTY_CSE, FACULTY_CSE_2, HOD_CSE

pytestmark = pytest.mark.django_db


def count(client, path):
    with CaptureQueriesContext(connection) as ctx:
        r = client.get(path)
    assert r.status_code == 200, r.content
    return len(ctx.captured_queries)


def _apply(actor, uid, n, substitute=None):
    for i in range(n):
        d = date(2026, 3, 9) + timedelta(days=7 * i)
        applications.submit(actor=actor(uid), data={
            "category": "CL", "start_date": d, "end_date": d, "purpose": "x",
            "substitute_user_id": substitute})


@pytest.mark.parametrize("path,uid", [("/api/v1/leave/requests", FACULTY_CSE),
                                      ("/api/v1/leave/queue", HOD_CSE)])
def test_constant_in_rows(configured, actor, client_for, path, uid):
    _apply(actor, FACULTY_CSE, 1)
    one = count(client_for(uid), path)
    _apply(actor, FACULTY_CSE_2, 3)
    assert count(client_for(uid), path) <= one


def test_substitutions_constant(configured, actor, client_for):
    _apply(actor, FACULTY_CSE, 1, substitute=HOD_CSE)
    one = count(client_for(HOD_CSE, as_role="faculty"), "/api/v1/leave/substitutions")
    _apply(actor, FACULTY_CSE_2, 3, substitute=HOD_CSE)
    assert count(client_for(HOD_CSE, as_role="faculty"), "/api/v1/leave/substitutions") <= one


def test_overview_is_bounded(configured, client_for):
    assert count(client_for(FACULTY_CSE), "/api/v1/leave/overview") <= 6
