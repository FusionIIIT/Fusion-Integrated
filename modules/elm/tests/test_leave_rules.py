from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.rules import validate_leave_details


def _valid(**overrides):
    values = {
        "start_date": date(2026, 10, 27),
        "end_date": date(2026, 10, 27),
        "leave_type": "CL",
        "duration_days": Decimal("1.0"),
        "is_half_day": False,
        "half_day_session": "",
        "reason": "Personal work",
        "station_leave": False,
        "station_leave_address": "",
        "out_of_station_from": None,
        "out_of_station_to": None,
    }
    values.update(overrides)
    return validate_leave_details(**values)


@pytest.mark.parametrize("duration", [Decimal("0"), Decimal("-0.5"), Decimal("0.6")])
def test_duration_must_be_positive_and_use_half_day_increments(duration):
    with pytest.raises(ValueError):
        _valid(duration_days=duration)


def test_half_day_must_be_one_date_and_half_a_day():
    assert _valid(
        duration_days=Decimal("0.5"),
        is_half_day=True,
        half_day_session="FN",
    ) == Decimal("0.5")
    with pytest.raises(ValueError, match="half-day request"):
        _valid(
            end_date=date(2026, 10, 28),
            duration_days=Decimal("0.5"),
            is_half_day=True,
            half_day_session="FN",
        )


def test_invalid_date_order_and_duration_span_are_rejected():
    with pytest.raises(ValueError, match="End date"):
        _valid(start_date=date(2026, 10, 28), end_date=date(2026, 10, 27))
    with pytest.raises(ValueError, match="calendar span"):
        _valid(duration_days=Decimal("2.0"))


def test_station_leave_requires_address_and_ordered_dates():
    with pytest.raises(ValueError, match="address"):
        _valid(station_leave=True)
    with pytest.raises(ValueError, match="Return date"):
        _valid(
            station_leave=True,
            station_leave_address="Jabalpur contact address",
            out_of_station_from=date(2026, 10, 28),
            out_of_station_to=date(2026, 10, 27),
        )


def test_half_day_is_only_available_for_casual_leave():
    with pytest.raises(ValueError, match="only for Casual Leave"):
        _valid(
            leave_type="EL", duration_days=Decimal("0.5"), is_half_day=True, half_day_session="FN"
        )


def test_cross_year_date_range_is_not_rejected_as_a_general_input_rule():
    assert _valid(
        start_date=date(2026, 12, 31),
        end_date=date(2027, 1, 1),
        duration_days=Decimal("2.0"),
    ) == Decimal("2.0")
