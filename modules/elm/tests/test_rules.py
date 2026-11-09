from datetime import date
from decimal import Decimal
import pytest

from modules.elm.domain.rules import (
    ENTITLEMENTS,
    count_leave_days,
    intervals_overlap,
    calculate_vl_to_el_conversion,
    validate_station_leave,
    can_substitute,
)

def test_entitlements_constants():
    assert ENTITLEMENTS['CL'] == Decimal('8')
    assert ENTITLEMENTS['RH'] == Decimal('2')
    assert ENTITLEMENTS['SCL'] == Decimal('15')
    assert ENTITLEMENTS['EL'] == Decimal('30')
    assert ENTITLEMENTS['VL'] == Decimal('60')
    assert ENTITLEMENTS['COL'] == Decimal('20')

def test_continuous_counting_el_vl_col():
    # 5 continuous days including weekend
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)
    closed = {date(2026, 10, 3), date(2026, 10, 4)}
    assert count_leave_days('EL', start, end, closed_dates=closed) == Decimal('5')
    assert count_leave_days('VL', start, end, closed_dates=closed) == Decimal('5')
    assert count_leave_days('COL', start, end, closed_dates=closed) == Decimal('5')

def test_working_days_counting_cl_scl_rh():
    # 5 calendar days with 2 closed days -> 3 working days
    start = date(2026, 10, 1)
    end = date(2026, 10, 5)
    closed = {date(2026, 10, 3), date(2026, 10, 4)}
    assert count_leave_days('CL', start, end, closed_dates=closed) == Decimal('3')
    assert count_leave_days('SCL', start, end, closed_dates=closed) == Decimal('3')
    assert count_leave_days('RH', start, end, closed_dates=closed) == Decimal('3')

def test_half_day_cl():
    d = date(2026, 10, 15)
    assert count_leave_days('CL', d, d, half_day='first') == Decimal('0.5')
    assert count_leave_days('CL', d, d, half_day='second') == Decimal('0.5')
    with pytest.raises(ValueError, match="Half-day CL must be on the same date"):
        count_leave_days('CL', date(2026, 10, 15), date(2026, 10, 16), half_day='first')

def test_intervals_overlap():
    d1 = date(2026, 10, 10)
    d2 = date(2026, 10, 15)
    # Distinct intervals do not overlap
    assert not intervals_overlap(d1, d2, None, date(2026, 10, 16), date(2026, 10, 20), None)
    # Intersecting intervals overlap
    assert intervals_overlap(d1, d2, None, date(2026, 10, 12), date(2026, 10, 18), None)
    # BR-EL-012: Opposite halves on the same day DO NOT overlap
    assert not intervals_overlap(d1, d1, 'first', d1, d1, 'second')
    assert not intervals_overlap(d1, d1, 'second', d1, d1, 'first')
    # Same half on same day overlaps
    assert intervals_overlap(d1, d1, 'first', d1, d1, 'first')

def test_calculate_vl_to_el_conversion():
    # 20 unused VL converts to 10 EL with room under 300 cap
    credited, forfeited, new_el = calculate_vl_to_el_conversion(
        unutilized_vl=Decimal('20'),
        current_el=Decimal('100'),
        max_el_cap=Decimal('300')
    )
    assert credited == Decimal('10')
    assert forfeited == Decimal('0')
    assert new_el == Decimal('110')

    # Fractional conversion: 15 unused VL converts to 7.5 EL
    credited, forfeited, new_el = calculate_vl_to_el_conversion(
        unutilized_vl=Decimal('15'),
        current_el=Decimal('100'),
        max_el_cap=Decimal('300')
    )
    assert credited == Decimal('7.5')
    assert forfeited == Decimal('0')
    assert new_el == Decimal('107.5')

    # Reaching 300 cap: current 295, 20 VL would be 10 EL, but cap allows only 5 EL
    credited, forfeited, new_el = calculate_vl_to_el_conversion(
        unutilized_vl=Decimal('20'),
        current_el=Decimal('295'),
        max_el_cap=Decimal('300')
    )
    assert credited == Decimal('5')
    assert forfeited == Decimal('10') # 5 EL * 2 = 10 VL converted, remaining 10 VL forfeited
    assert new_el == Decimal('300')

def test_validate_station_leave():
    assert validate_station_leave(False, None, None) is True
    assert validate_station_leave(True, "Bhopal", "+919876543210") is True
    assert validate_station_leave(True, "", "+919876543210") is False
    assert validate_station_leave(True, "Bhopal", "   ") is False

def test_can_substitute():
    assert can_substitute(101, 102) is True
    assert can_substitute(101, 101) is False
