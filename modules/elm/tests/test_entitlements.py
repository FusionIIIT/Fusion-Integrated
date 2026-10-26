import pytest
from django.utils import timezone
from modules.elm.services.entitlements import credit_annual_entitlements, get_balance


@pytest.mark.django_db
def test_non_faculty_entitlements():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    assert get_balance(1, "CL", 2026) == 8
    assert get_balance(1, "RH", 2026) == 2
    assert get_balance(1, "SCL", 2026) == 15
    assert get_balance(1, "COL", 2026) == 20
    assert get_balance(1, "EL", 2026) == 30
    assert get_balance(1, "VL", 2026) == 0


@pytest.mark.django_db
def test_faculty_entitlements():
    credit_annual_entitlements(1, 2026, is_faculty=True)
    assert get_balance(1, "CL", 2026) == 8
    assert get_balance(1, "RH", 2026) == 2
    assert get_balance(1, "SCL", 2026) == 15
    assert get_balance(1, "COL", 2026) == 20
    assert get_balance(1, "EL", 2026) == 0
    assert get_balance(1, "VL", 2026) == 60


@pytest.mark.django_db
def test_credit_twice():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    credit_annual_entitlements(1, 2026, is_faculty=False)
    assert get_balance(1, "CL", 2026) == 8
