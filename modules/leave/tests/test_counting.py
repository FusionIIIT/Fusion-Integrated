from datetime import datetime
from decimal import Decimal

import pytest  # Add this line to import pytest

from modules.leave.domain.counting import count_leave_days


def test_el_full_week_no_holidays():
    start_date = datetime(2026, 10, 5)
    end_date = datetime(2026, 10, 9)
    category = 'EL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_el_week_with_weekends():
    start_date = datetime(2026, 10, 9)
    end_date = datetime(2026, 10, 12)
    category = 'EL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('4')


def test_el_week_with_holiday():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 10, 7)
    category = 'EL'
    half_day = False
    holidays = {datetime(2026, 10, 7)}

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_col_full_week_no_holidays():
    start_date = datetime(2026, 10, 5)
    end_date = datetime(2026, 10, 9)
    category = 'COL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_col_week_with_weekends():
    start_date = datetime(2026, 10, 9)
    end_date = datetime(2026, 10, 12)
    category = 'COL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('4')


def test_col_week_with_holiday():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 10, 7)
    category = 'COL'
    half_day = False
    holidays = {datetime(2026, 10, 7)}

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_vl_full_week_no_holidays():
    start_date = datetime(2026, 10, 5)
    end_date = datetime(2026, 10, 9)
    category = 'VL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_vl_week_with_weekends():
    start_date = datetime(2026, 10, 9)
    end_date = datetime(2026, 10, 12)
    category = 'VL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('4')


def test_vl_week_with_holiday():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 10, 7)
    category = 'VL'
    half_day = False
    holidays = {datetime(2026, 10, 7)}

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('5')


def test_cl_half_day():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 10, 3)
    category = 'CL'
    half_day = True
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('0.5')


def test_cl_full_day():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 10, 3)
    category = 'CL'
    half_day = False
    holidays = set()

    assert count_leave_days(category, start_date, end_date, half_day, holidays) == Decimal('1')


def test_end_date_before_start_date():
    start_date = datetime(2026, 10, 3)
    end_date = datetime(2026, 9, 3)
    category = 'EL'
    half_day = False
    holidays = set()

    with pytest.raises(ValueError):
        count_leave_days(category, start_date, end_date, half_day, holidays)
