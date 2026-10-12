"""The boundary sweep: lapse, convert, carry — and never twice."""
from __future__ import annotations

from decimal import Decimal

import pytest

from modules.leave.models import LeaveBalance, LeaveYearRun
from modules.leave.services import yearend
from modules.leave.tests.conftest import APPLICANT, DIRECTOR, UNIT_HEAD

pytestmark = pytest.mark.django_db


def _balance(uid, category, year, **kw):
    return LeaveBalance.objects.create(
        user_id=uid, category=category, year=year,
        credited=Decimal(kw.get("credited", 0)),
        used=Decimal(kw.get("used", 0)),
        carried_forward=Decimal(kw.get("carried", 0)))


def _available(uid, category, year) -> Decimal:
    # Materialise-on-read, exactly as the production balance screen does:
    # a hole shows up as zero, not as a missing row.
    row, _ = LeaveBalance.objects.get_or_create(
        user_id=uid, category=category, year=year)
    return row.carried_forward + row.credited + row.adjusted - row.used


def test_year_end_lapse_convert_carry(stub_iam, desks):
    # UNIT_HEAD is faculty: their VL converts; their CL and SCL lapse;
    # their EL carries as itself.
    _balance(UNIT_HEAD, "cl", 2026, credited="5")
    _balance(UNIT_HEAD, "scl", 2026, credited="1.5")
    _balance(UNIT_HEAD, "vl", 2026, credited="60", used="50")
    _balance(UNIT_HEAD, "el", 2026, credited="10")
    # APPLICANT is staff: staff VL lapses rather than converting.
    _balance(APPLICANT, "vl", 2026, credited="4")

    report = yearend.run_year_end(2026)
    assert report["already_run"] is False

    assert _available(UNIT_HEAD, "cl", 2026) == 0
    assert _available(UNIT_HEAD, "scl", 2026) == 0
    assert _available(UNIT_HEAD, "vl", 2026) == 0
    assert _available(UNIT_HEAD, "el", 2026) == 0      # carried out
    # 10 unused VL → 5 EL conversion; plus the 10 EL that carried as itself.
    assert _available(UNIT_HEAD, "el", 2027) == Decimal("15.00")
    assert _available(APPLICANT, "vl", 2026) == 0
    assert _available(APPLICANT, "el", 2027) == 0      # nothing converted


def test_year_end_is_idempotent(stub_iam, desks):
    _balance(UNIT_HEAD, "cl", 2026, credited="5")
    first = yearend.run_year_end(2026)
    second = yearend.run_year_end(2026)
    assert first["already_run"] is False
    assert second["already_run"] is True
    assert second["entries"] == first["entries"]
    # The lapse happened exactly once.
    assert LeaveYearRun.objects.count() == 1
    assert _available(UNIT_HEAD, "cl", 2026) == 0


def test_directors_vl_also_converts(stub_iam, desks):
    _balance(DIRECTOR, "vl", 2026, credited="60", used="60")
    yearend.run_year_end(2026)
    # 60 taken, 0 left: nothing to convert, nothing to carry.
    assert _available(DIRECTOR, "vl", 2026) == 0
    assert not LeaveBalance.objects.filter(user_id=DIRECTOR, year=2027,
                                           category="el").exists()
