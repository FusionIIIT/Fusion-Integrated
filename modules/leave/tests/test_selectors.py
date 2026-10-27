"""Tests for leave selectors."""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.models import LeaveApplication, LeaveBalance, LeaveCategory
from modules.leave.selectors.applications import applications_for, balances_for

pytestmark = pytest.mark.django_db

# Helper class for testing
class DummyPrincipal:
    def __init__(self, user_id=None, permissions=()):
        self.user_id = user_id
        self.permissions = set(permissions)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

@pytest.fixture
def principal_admin():
    return DummyPrincipal(permissions=["leave_management.application.view", "leave_management.balance.view"])

@pytest.fixture
def principal_user_1():
    return DummyPrincipal(user_id=1)

@pytest.fixture
def principal_user_2():
    return DummyPrincipal(user_id=2)

@pytest.fixture
def principal_user_3():
    return DummyPrincipal(user_id=3)

@pytest.fixture
def principal_anonymous():
    return DummyPrincipal(user_id=None)

@pytest.fixture
def category():
    return LeaveCategory.objects.create(code="CL", name="Casual Leave")

@pytest.fixture
def leave_application_1_own(category):
    return LeaveApplication.objects.create(
        user_id=1, category=category, start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2), reason="Personal", substitute_user_id=None
    )

@pytest.fixture
def leave_application_2_own(category):
    return LeaveApplication.objects.create(
        user_id=2, category=category, start_date=date(2026, 1, 3),
        end_date=date(2026, 1, 4), reason="Medical", substitute_user_id=None
    )

@pytest.fixture
def leave_application_1_substitute_3(category):
    return LeaveApplication.objects.create(
        user_id=1, category=category, start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 6), reason="Conference", substitute_user_id=3
    )

@pytest.fixture
def leave_balance_1(category):
    return LeaveBalance.objects.create(
        user_id=1, category=category, year=2026, balance_days=Decimal("8.0")
    )

@pytest.fixture
def leave_balance_2(category):
    return LeaveBalance.objects.create(
        user_id=2, category=category, year=2026, balance_days=Decimal("8.0")
    )

@pytest.fixture
def leave_balance_3(category):
    return LeaveBalance.objects.create(
        user_id=3, category=category, year=2026, balance_days=Decimal("8.0")
    )


def test_applications_for_own_only(principal_user_1, leave_application_1_own, leave_application_2_own):
    # User 1 should only see their own application
    results = applications_for(principal_user_1)
    assert results.count() == 1
    assert results.first().pk == leave_application_1_own.pk

def test_applications_for_substitute(principal_user_3, leave_application_1_substitute_3):
    # User 3 (substitute) should see the application
    results = applications_for(principal_user_3)
    assert results.count() == 1
    assert results.first().pk == leave_application_1_substitute_3.pk

def test_applications_for_reviewer_sees_all(principal_admin, leave_application_1_own, leave_application_2_own, leave_application_1_substitute_3):
    # Admin should see all applications
    results = applications_for(principal_admin)
    assert results.count() == 3

def test_applications_for_anonymous_none(principal_anonymous):
    # Anonymous user should see none
    results = applications_for(principal_anonymous)
    assert results.count() == 0

def test_balances_for_own_only(principal_user_1, leave_balance_1, leave_balance_2):
    # User 1 should only see their own balance
    results = balances_for(principal_user_1)
    assert results.count() == 1
    assert results.first().pk == leave_balance_1.pk

def test_balances_for_manager_sees_all(principal_admin, leave_balance_1, leave_balance_2, leave_balance_3):
    # Admin should see all balances
    results = balances_for(principal_admin)
    assert results.count() == 3

def test_balances_for_anonymous_none(principal_anonymous):
    # Anonymous user should see none
    results = balances_for(principal_anonymous)
    assert results.count() == 0
