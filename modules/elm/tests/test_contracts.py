"""Tests for ELM public cross-module contracts (contracts.py)."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm import contracts
from modules.elm.models import LeaveAccount, LeaveApplication


@pytest.mark.django_db
def test_get_leave_balances_contract():
    # Setup leave accounts for user 101
    LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        carried_forward=Decimal("0.00"),
        availed=Decimal("2.00"),
        balance=Decimal("6.00"),
    )
    LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="EL",
        credited=Decimal("30.00"),
        carried_forward=Decimal("10.00"),
        availed=Decimal("5.00"),
        balance=Decimal("35.00"),
    )

    result = contracts.get_leave_balances([101, 999], year=2026)
    assert 101 in result
    user_balances = result[101]
    assert len(user_balances) == 2

    cl = next(b for b in user_balances if b.category == "CL")
    assert cl.balance == Decimal("6.00")
    assert cl.availed == Decimal("2.00")

    el = next(b for b in user_balances if b.category == "EL")
    assert el.balance == Decimal("35.00")

    # User 999 has no accounts
    assert result[999] == ()


@pytest.mark.django_db
def test_get_active_leaves_contract():
    app1 = LeaveApplication.objects.create(
        user_id=201,
        category="CL",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        chargeable_days=Decimal("20.00"),
        purpose="Tour",
        status="approved",
    )
    # Draft or rejected is not active
    LeaveApplication.objects.create(
        user_id=201,
        category="EL",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 15),
        chargeable_days=Decimal("15.00"),
        purpose="Pending",
        status="draft",
    )

    result = contracts.get_active_leaves([201, 202], on_date=date(2026, 10, 15))
    assert 201 in result
    assert len(result[201]) == 1
    assert result[201][0].id == app1.id
    assert result[201][0].category == "CL"
    assert result[202] == ()


@pytest.mark.django_db
def test_get_leave_applications_contract():
    app = LeaveApplication.objects.create(
        user_id=301,
        category="RH",
        start_date=date(2026, 11, 4),
        end_date=date(2026, 11, 4),
        chargeable_days=Decimal("1.00"),
        purpose="Festival",
        status="approved",
    )

    result = contracts.get_leave_applications([app.id, 9999])
    assert app.id in result
    dto = result[app.id]
    assert dto.user_id == 301
    assert dto.category == "RH"
    assert dto.status == "approved"
    assert 9999 not in result
