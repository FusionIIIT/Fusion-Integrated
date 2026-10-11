"""Domain tests: pure Python, no database."""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import state_machine as sm
from modules.leave.domain.calendar import PublishedCalendar
from modules.leave.domain.categories import CL, COL, EL, VL
from modules.leave.domain.counting import chargeable_days
from modules.leave.domain.eligibility import (
    LeaveRequest, OccupiedInterval, ValidationError, canonical_policy, overlaps,
    validate_request,
)
from modules.leave.domain.ledger import convert_vl_to_el, year_end_entries


def test_half_day_cl_is_half(BR_EL_010=None):
    d = date(2026, 3, 4)  # Wednesday
    assert chargeable_days(category=CL, start=d, end=d, half="first",
                           closed_holidays=frozenset()) == Decimal("0.5")


def test_el_counts_weekend_inside_interval():
    # Friday to Monday inclusive = 4 calendar days (BR-EL-011)
    days = chargeable_days(
        category=EL, start=date(2026, 3, 6), end=date(2026, 3, 9),
        half=None, closed_holidays=frozenset())
    assert days == Decimal("4")


def test_cl_does_not_count_weekend():
    days = chargeable_days(
        category=CL, start=date(2026, 3, 6), end=date(2026, 3, 9),
        half=None, closed_holidays=frozenset())
    assert days == Decimal("2")


def test_half_day_cl_same_date_different_halves_do_not_overlap():
    a = OccupiedInterval(date(2026, 3, 4), date(2026, 3, 4), "first", CL)
    b = OccupiedInterval(date(2026, 3, 4), date(2026, 3, 4), "second", CL)
    assert not overlaps(a, b)


def test_vl_to_el_allows_fraction():
    policy = canonical_policy()
    assert convert_vl_to_el(Decimal("5"), policy) == Decimal("2.50")


def test_year_end_lapses_cl_and_converts_faculty_vl():
    policy = canonical_policy()
    rows = year_end_entries(
        kind="faculty", year=2026,
        balances={"CL": Decimal("3"), "RH": Decimal("0"), "SCL": Decimal("1"),
                  "VL": Decimal("10"), "EL": Decimal("4"), "COL": Decimal("2")},
        policy=policy)
    kinds = {(c, t) for c, t, _a, _m in rows}
    assert ("CL", "lapse") in kinds
    assert ("SCL", "lapse") in kinds
    assert ("VL", "lapse") in kinds
    assert ("EL", "conversion") in kinds


def test_rh_must_match_published_date():
    policy = canonical_policy()
    cal = PublishedCalendar(frozenset(), frozenset({date(2026, 10, 2)}), ())
    req = LeaveRequest(
        category="RH", start=date(2026, 10, 3), end=date(2026, 10, 3),
        half=None, station_leave=False, medical_evidence=False,
        purpose="RH", applicant_kind="staff", requires_substitute=False)
    with pytest.raises(ValidationError) as exc:
        validate_request(request=req, policy=policy, calendar=cal,
                         balance=Decimal("2"), occupied=())
    assert exc.value.code == "BR-EL-003"


def test_faculty_cannot_take_vl_outside_vacation():
    policy = canonical_policy()
    cal = PublishedCalendar(frozenset(), frozenset(),
                            ((date(2026, 5, 1), date(2026, 6, 15)),))
    req = LeaveRequest(
        category=VL, start=date(2026, 7, 1), end=date(2026, 7, 5),
        half=None, station_leave=False, medical_evidence=False,
        purpose="vacation", applicant_kind="faculty", requires_substitute=False)
    with pytest.raises(ValidationError) as exc:
        validate_request(request=req, policy=policy, calendar=cal,
                         balance=Decimal("60"), occupied=())
    assert exc.value.code == "BR-EL-006"


def test_staff_are_not_eligible_for_vl():
    policy = canonical_policy()
    cal = PublishedCalendar(frozenset(), frozenset(),
                            ((date(2026, 5, 1), date(2026, 6, 15)),))
    req = LeaveRequest(
        category=VL, start=date(2026, 5, 2), end=date(2026, 5, 5),
        half=None, station_leave=False, medical_evidence=False,
        purpose="vacation", applicant_kind="staff", requires_substitute=False)
    with pytest.raises(ValidationError) as exc:
        validate_request(request=req, policy=policy, calendar=cal,
                         balance=Decimal("60"), occupied=())
    assert exc.value.code == "BR-EL-001"


def test_unit_head_cannot_finally_reject_higher_sanction_from_table():
    events = {t.event for t in sm.TRANSITIONS
              if t.frm == sm.AWAITING_UNIT_HEAD and t.to == sm.REJECTED}
    assert events == {"unit_head_reject"}
    rejected = [t for t in sm.TRANSITIONS
                if t.frm == sm.AWAITING_UNIT_HEAD and t.to == sm.REJECTED]
    assert all("cl_or_rh" in t.guards for t in rejected)
