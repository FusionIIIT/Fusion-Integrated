"""Tests for the leave module public cross-module contract."""

import dataclasses
from decimal import Decimal

import pytest
from freezegun import freeze_time

from modules.leave.contracts import LeaveSummaryDTO, get_leave_summaries
from modules.leave.models import LeaveBalance, LeaveType


@pytest.fixture
def leave_types(db):
    types = {}
    for code, name in [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]:
        lt, _ = LeaveType.objects.get_or_create(code=code, defaults={"name": name})
        types[code] = lt
    return types


@pytest.mark.django_db
def test_get_leave_summaries_empty_and_falsy():
    assert get_leave_summaries([]) == {}
    assert get_leave_summaries([None]) == {}
    assert get_leave_summaries((None, None)) == {}


@pytest.mark.django_db
def test_get_leave_summaries_no_balance_records():
    summaries = get_leave_summaries([991, 992])
    assert set(summaries.keys()) == {991, 992}

    s991 = summaries[991]
    assert isinstance(s991, LeaveSummaryDTO)
    assert s991.user_id == 991
    assert s991.cl_available == Decimal("0.0")
    assert s991.rh_available == Decimal("0.0")
    assert s991.scl_available == Decimal("0.0")
    assert s991.el_available == Decimal("0.0")
    assert s991.col_available == Decimal("0.0")
    assert s991.vl_available == Decimal("0.0")


@pytest.mark.django_db
@freeze_time("2026-06-15")
def test_get_leave_summaries_current_year_filtering(leave_types):
    # Previous year 2025 balances
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2025,
        credited_days=Decimal("8.0"),
        available_days=Decimal("3.0"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["EL"],
        year=2025,
        credited_days=Decimal("30.0"),
        available_days=Decimal("12.0"),
    )

    # Current year 2026 balances
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("7.5"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["EL"],
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("25.0"),
    )

    # Future year 2027 balances
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2027,
        credited_days=Decimal("8.0"),
        available_days=Decimal("1.0"),
    )

    summaries = get_leave_summaries([101])
    assert 101 in summaries
    s = summaries[101]
    assert s.cl_available == Decimal("7.5")
    assert s.el_available == Decimal("25.0")
    assert s.rh_available == Decimal("0.0")


@pytest.mark.django_db
@freeze_time("2026-06-15")
def test_get_leave_summaries_multiple_users_correct_values(leave_types):
    # User 101 has CL, RH, EL
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("6.5"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["RH"],
        year=2026,
        credited_days=Decimal("2.0"),
        available_days=Decimal("2.0"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["EL"],
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("20.0"),
    )

    # User 102 has SCL, COL, VL
    LeaveBalance.objects.create(
        user_id=102,
        leave_type=leave_types["SCL"],
        year=2026,
        credited_days=Decimal("15.0"),
        available_days=Decimal("10.0"),
    )
    LeaveBalance.objects.create(
        user_id=102,
        leave_type=leave_types["COL"],
        year=2026,
        credited_days=Decimal("10.0"),
        available_days=Decimal("5.0"),
    )
    LeaveBalance.objects.create(
        user_id=102,
        leave_type=leave_types["VL"],
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("18.0"),
    )

    # User 103 has no balance records in current year
    summaries = get_leave_summaries([101, 102, 103])
    assert set(summaries.keys()) == {101, 102, 103}

    s101 = summaries[101]
    assert s101.cl_available == Decimal("6.5")
    assert s101.rh_available == Decimal("2.0")
    assert s101.el_available == Decimal("20.0")
    assert s101.scl_available == Decimal("0.0")
    assert s101.col_available == Decimal("0.0")
    assert s101.vl_available == Decimal("0.0")

    s102 = summaries[102]
    assert s102.cl_available == Decimal("0.0")
    assert s102.rh_available == Decimal("0.0")
    assert s102.el_available == Decimal("0.0")
    assert s102.scl_available == Decimal("10.0")
    assert s102.col_available == Decimal("5.0")
    assert s102.vl_available == Decimal("18.0")

    s103 = summaries[103]
    assert s103.cl_available == Decimal("0.0")
    assert s103.rh_available == Decimal("0.0")
    assert s103.el_available == Decimal("0.0")
    assert s103.scl_available == Decimal("0.0")
    assert s103.col_available == Decimal("0.0")
    assert s103.vl_available == Decimal("0.0")


@pytest.mark.django_db
@freeze_time("2026-06-15")
def test_get_leave_summaries_query_boundedness(leave_types, django_assert_num_queries):
    # Seed balances for multiple users
    for uid in range(201, 211):
        LeaveBalance.objects.create(
            user_id=uid,
            leave_type=leave_types["CL"],
            year=2026,
            credited_days=Decimal("8.0"),
            available_days=Decimal("5.0"),
        )
        LeaveBalance.objects.create(
            user_id=uid,
            leave_type=leave_types["EL"],
            year=2026,
            credited_days=Decimal("30.0"),
            available_days=Decimal("20.0"),
        )

    user_batch = [*range(201, 211), 998, 999]
    # Contract must execute exactly 1 database query regardless of batch size
    with django_assert_num_queries(1):
        results = get_leave_summaries(user_batch)

    assert len(results) == len(user_batch)
    for uid in range(201, 211):
        assert results[uid].cl_available == Decimal("5.0")
        assert results[uid].el_available == Decimal("20.0")
    assert results[998].cl_available == Decimal("0.0")


@pytest.mark.django_db
def test_get_leave_summaries_consumer_compatibility():
    summaries = get_leave_summaries([101, 101, None])
    assert len(summaries) == 1
    s = summaries[101]

    # Verify DTO type and immutability
    assert isinstance(s, LeaveSummaryDTO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.cl_available = Decimal("10.0")  # type: ignore[misc]

    # Verify all expected attribute names exist and are Decimals
    for field_name in (
        "cl_available",
        "rh_available",
        "scl_available",
        "el_available",
        "col_available",
        "vl_available",
    ):
        assert hasattr(s, field_name)
        assert isinstance(getattr(s, field_name), Decimal)
