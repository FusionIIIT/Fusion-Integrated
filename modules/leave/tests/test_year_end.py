"""Year end: lapse, carry forward, convert, and never do it twice."""
from decimal import Decimal

import pytest

from modules.leave.domain import categories as cat
from modules.leave.domain import ledger as led
from modules.leave.models import LeaveLedgerEntry
from modules.leave.services import accounts as account_service
from modules.leave.services import yearend

pytestmark = pytest.mark.django_db


def _account(user_id=1001, year=2026, category=cat.CL, *, credit=None, debit=None):
    account = account_service.ensure_account(user_id=user_id, year=year,
                                             category=category)
    if credit is not None:
        account_service.post(account=account, entry_type=led.ACCRUAL, days=credit,
                             reference=f"year:{year}")
    if debit is not None:
        account_service.post(account=account, entry_type=led.DEBIT, days=debit,
                             reference="request:1")
    return account


def test_unused_cl_lapses(configured):
    account = _account(category=cat.CL, credit=8, debit=3)
    report = yearend.run(year=2026)
    assert report["lapsed"] == Decimal(5)
    assert account.balance() == Decimal(0)


def test_unused_el_carries_forward(configured):
    account = _account(category=cat.EL, credit=30, debit=10)
    report = yearend.run(year=2026)
    assert report["carried"] == Decimal(20)
    assert account.balance() == Decimal(20)


def test_unused_vl_converts_at_two_to_one(configured):
    account = _account(category=cat.VL, credit=5)
    report = yearend.run(year=2026)
    assert report["converted_el"] == Decimal("2.5")
    assert account.balance() == Decimal("2.5")
    assert account.entries.filter(entry_type=led.CONVERSION_OUT).exists()


def test_converted_vl_lands_in_the_next_year_s_el(configured):
    _account(category=cat.VL, credit=5)
    yearend.run(year=2026)

    account_service.open_year(user_id=1001, year=2027, is_faculty=True)
    el = account_service.ensure_account(user_id=1001, year=2027, category=cat.EL)
    opening = el.entries.filter(entry_type=led.OPENING).first()
    assert opening is not None and opening.days == Decimal("2.50")


def test_year_end_is_idempotent(configured):
    _account(category=cat.CL, credit=8, debit=3)
    yearend.run(year=2026)
    after_first = LeaveLedgerEntry.objects.filter(reference="yearend:2026").count()
    assert after_first > 0

    yearend.run(year=2026)
    assert LeaveLedgerEntry.objects.filter(reference="yearend:2026").count() == after_first


def test_an_empty_account_is_left_alone(configured):
    report = yearend.run(year=2026)
    assert report["accounts"] == 0
    assert report["exceptions"] == []


def test_opening_a_year_credits_the_entitlement_once(configured):
    account_service.open_year(user_id=1001, year=2026, is_faculty=False)
    account_service.open_year(user_id=1001, year=2026, is_faculty=False)
    account = account_service.ensure_account(user_id=1001, year=2026, category=cat.CL)
    assert account.entries.filter(entry_type=led.ACCRUAL).count() == 1
    assert account.balance() == Decimal(8)


def test_a_faculty_member_gets_vl_and_a_staff_member_does_not(configured):
    faculty = account_service.open_year(user_id=9001, year=2026, is_faculty=True)
    staff = account_service.open_year(user_id=9002, year=2026, is_faculty=False)
    assert cat.VL in faculty
    assert cat.VL not in staff
