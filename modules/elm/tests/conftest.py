"""Fixtures shared by elm's tests. Sessions are minted, never seeded in the IAM."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveType
from modules.elm.tests.support import ADMIN_PERMS, APPROVER_PERMS, EMPLOYEE_PERMS, principal


@pytest.fixture
def employee():
    return principal(user_id=1001)


@pytest.fixture
def approver():
    return principal(user_id=2002, permissions=APPROVER_PERMS, kind="faculty",
                     roles=("Leave Approver",), active_role="Leave Approver")


@pytest.fixture
def administrator():
    return principal(user_id=3003, permissions=ADMIN_PERMS, kind="staff",
                     roles=("Leave Administrator",),
                     active_role="Leave Administrator")


@pytest.fixture
def permissions():
    """The sets, for tests that build principals of their own."""
    return {"employee": EMPLOYEE_PERMS, "approver": APPROVER_PERMS,
            "admin": ADMIN_PERMS}


@pytest.fixture
def make_type():
    """A leave type effective a month ago, so it is live today."""
    def _make(code="CL", name="Casual Leave", entitlement="8.0", **kw):
        kw.setdefault("allows_half_day", True)
        return LeaveType.objects.create(
            code=code, name=name,
            annual_entitlement_days=Decimal(entitlement),
            effective_from=timezone.localdate() - timedelta(days=30), **kw)
    return _make


@pytest.fixture
def next_monday():
    today = timezone.localdate()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


@pytest.fixture
def api(stub_iam):
    """An authenticated APIClient; pass the session fields you want."""
    def _client(**session_kwargs):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token elm-test")
        stub_iam(make_session(**session_kwargs))
        return client
    return _client


@pytest.fixture
def anon_client():
    return APIClient()
