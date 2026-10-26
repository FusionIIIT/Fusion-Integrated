import datetime
from modules.leave.domain.overlap import requests_overlap


def test_disjoint_dates_false():
    start_new = datetime.date(2024, 1, 1)
    end_new = datetime.date(2024, 1, 3)
    start_old = datetime.date(2024, 1, 5)
    end_old = datetime.date(2024, 1, 7)
    assert not requests_overlap(start_new, end_new, start_old, end_old, "CL", "CL", "full_day", "full_day")


def test_intersecting_ranges_true():
    start_new = datetime.date(2024, 1, 1)
    end_new = datetime.date(2024, 1, 5)
    start_old = datetime.date(2024, 1, 4)
    end_old = datetime.date(2024, 1, 6)
    assert requests_overlap(start_new, end_new, start_old, end_old, "CL", "CL", "full_day", "full_day")


def test_same_day_cl_different_halves_false():
    d = datetime.date(2024, 1, 10)
    assert not requests_overlap(d, d, d, d, "CL", "CL", "first_half", "second_half")


def test_same_day_cl_same_half_true():
    d = datetime.date(2024, 1, 11)
    assert requests_overlap(d, d, d, d, "CL", "CL", "first_half", "first_half")


def test_same_day_cl_and_el_opposite_halves_true():
    d = datetime.date(2024, 1, 12)
    assert requests_overlap(d, d, d, d, "CL", "EL", "first_half", "second_half")


def test_overlapping_multi_day_opposite_cl_halves_true():
    start_new = datetime.date(2024, 1, 15)
    end_new = datetime.date(2024, 1, 17)
    start_old = datetime.date(2024, 1, 16)
    end_old = datetime.date(2024, 1, 18)
    # new request is first_half on 16, old request is second_half on 16
    assert requests_overlap(start_new, end_new, start_old, end_old, "CL", "CL", "first_half", "second_half")
