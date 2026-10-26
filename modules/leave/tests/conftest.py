"""Shared fixtures for ELM API tests: a unit with a head, and an authenticated client."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveBalance, OrgUnit


@pytest.fixture
def unit(db):
    return OrgUnit.objects.create(name="CSE", unit_head_user_id=500)


@pytest.fixture
def balances(db):
    for user_id in (101, 202):
        for category in ("CL", "RH", "SCL", "EL", "COL", "VL"):
            LeaveBalance.objects.create(
                user_id=user_id,
                year=2030,
                category=category,
                entitled=Decimal("30"),
                used=Decimal("0"),
            )


@pytest.fixture
def as_user(stub_iam):
    """as_user(user_id, *permissions) -> an APIClient authenticated as that employee."""

    def _make(user_id, *permissions, kind="faculty"):
        stub_iam(
            make_session(user_id=user_id, kind=kind, modules=("leave",), permissions=permissions)
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client

    return _make
