"""Domain tests: pure Python, no database."""
import datetime
import pytest

from modules.leave.domain import entitlement as ent
from modules.leave.domain import state_machine as sm


def test_table_is_spec():
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm, to in declared:
        assert sm.is_legal(frm, to) is True


def test_illegal_raises():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.CANCELLED)

    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.APPROVED, sm.DRAFT)

    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.DRAFT, sm.APPROVED, sm.EMPLOYEE)


def test_terminal_have_no_exits():
    for s in sm.TERMINAL:
        assert sm.allowed_targets(s) == []
    # Approved can be cancelled before start date (BR-EL-023)
    assert sm.allowed_targets(sm.APPROVED) == [sm.CANCELLED]


def test_entitlement_values():
    assert ent.yearly_credit("CL") == 8.0
    assert ent.yearly_credit("RH") == 2.0
    assert ent.yearly_credit("EL") == 30.0
    assert ent.yearly_credit("COL") == 20.0
    assert ent.yearly_credit("VL") == 60.0
    assert ent.carries_forward("EL") is True
    assert ent.carries_forward("COL") is True
    assert ent.carries_forward("CL") is False
    assert ent.vl_to_el(60.0) == 30.0


def test_calculate_days_continuous_and_non_continuous():
    # Friday 2026-10-23 to Monday 2026-10-26 (Fri, Sat, Sun, Mon)
    start = datetime.date(2026, 10, 23)
    end = datetime.date(2026, 10, 26)

    # EL is continuous: includes weekends -> 4 days
    assert ent.calculate_days("EL", start, end) == 4.0

    # CL excludes weekends: Friday + Monday -> 2 days
    assert ent.calculate_days("CL", start, end) == 2.0

    # Half day CL
    assert ent.calculate_days("CL", start, start, half_day=True) == 0.5


def test_non_overlap_validation():
    class FakeReq:
        def __init__(self, start, end, cat="CL", half=False, period="none", status="approved", pk=1):
            self.start_date = start
            self.end_date = end
            self.category = cat
            self.half_day = half
            self.half_day_period = period
            self.status = status
            self.pk = pk

    existing = [FakeReq(datetime.date(2026, 11, 2), datetime.date(2026, 11, 4))]

    # Overlapping span
    with pytest.raises(ent.OverlapError):
        ent.validate_non_overlap(existing, datetime.date(2026, 11, 3), datetime.date(2026, 11, 5))

    # Non-overlapping span
    ent.validate_non_overlap(existing, datetime.date(2026, 11, 5), datetime.date(2026, 11, 6))

    # Half-day CL exception on same day (BR-EL-012)
    single_day_fn = [FakeReq(datetime.date(2026, 11, 10), datetime.date(2026, 11, 10),
                             cat="CL", half=True, period="FN")]
    # Applying for AN on same day is permitted
    ent.validate_non_overlap(single_day_fn, datetime.date(2026, 11, 10), datetime.date(2026, 11, 10),
                            new_half_day=True, new_period="AN")

    # Applying for duplicate FN on same day raises OverlapError
    with pytest.raises(ent.OverlapError):
        ent.validate_non_overlap(single_day_fn, datetime.date(2026, 11, 10), datetime.date(2026, 11, 10),
                                new_half_day=True, new_period="FN")
