"""The list endpoint's query count is constant in row count (Step 5.8)."""
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.elm.models import LeaveApplication
from modules.elm.tests.support import EMPLOYEE_PERMS

pytestmark = pytest.mark.django_db

BASE = "/api/v1/elm"


def _queries(client, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx.captured_queries)


def _make_application(leave_type, day, user_id=1001):
    return LeaveApplication.objects.create(
        user_id=user_id, leave_type=leave_type, start_date=day, end_date=day,
        days=1)


def test_the_application_list_is_constant_in_row_count(api, make_type,
                                                       next_monday):
    leave_type = make_type()
    for week in range(2):
        _make_application(leave_type, next_monday + timedelta(weeks=week))
    client = api(user_id=1001, permissions=EMPLOYEE_PERMS, modules=("elm",))
    small = _queries(client, f"{BASE}/applications")

    for week in range(2, 8):
        _make_application(leave_type, next_monday + timedelta(weeks=week))
    big = _queries(client, f"{BASE}/applications")

    assert small == big


def test_the_approvals_inbox_is_constant_in_row_count(api, make_type,
                                                      next_monday):
    leave_type = make_type()
    for week in range(2):
        _make_application(leave_type, next_monday + timedelta(weeks=week),
                          user_id=500 + week)
    client = api(user_id=2002,
                 permissions=("elm.application.view", "elm.application.approve"),
                 modules=("elm",), kind="faculty", roles=("Leave Approver",),
                 active_role="Leave Approver")
    small = _queries(client, f"{BASE}/approvals")

    for week in range(2, 8):
        _make_application(leave_type, next_monday + timedelta(weeks=week),
                          user_id=500 + week)
    big = _queries(client, f"{BASE}/approvals")

    assert small == big
