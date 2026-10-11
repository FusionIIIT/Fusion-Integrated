"""HR contracts.py public surface tests."""
import datetime

import pytest

from modules.hr.contracts import get_employments
from modules.hr.models import Department, EmploymentContract


@pytest.fixture
def dept(db):
    return Department.objects.create(name="CSE", code="CSE")


@pytest.mark.django_db
def test_employed_user_is_found(dept):
    EmploymentContract.objects.create(
        user_id=1001, department=dept, title="Prof",
        kind="permanent", status="active", starts_on=datetime.date(2025, 1, 1),
    )
    result = get_employments([1001])
    assert result[1001].is_employed is True
    assert result[1001].department_name == "CSE"
    assert result[1001].title == "Prof"


@pytest.mark.django_db
def test_unknown_user_is_not_employed(dept):
    result = get_employments([9999])
    assert result[9999].is_employed is False


@pytest.mark.django_db
def test_empty_input_returns_empty(dept):
    assert get_employments([]) == {}


@pytest.mark.django_db
def test_ended_contract_not_reported_as_employed(dept):
    EmploymentContract.objects.create(
        user_id=1002, department=dept, title="Staff",
        kind="temporary", status="ended", starts_on=datetime.date(2024, 1, 1),
        ends_on=datetime.date(2024, 12, 31), ended_by_user_id=9001,
    )
    result = get_employments([1002])
    assert result[1002].is_employed is False
