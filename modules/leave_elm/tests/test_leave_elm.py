import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from modules.leave_elm.api.serializers import LeaveApplicationCreateSerializer
from modules.leave_elm.api.views import calculate_leave_days
from modules.leave_elm.models import LeaveStatus, LeaveType


def test_leave_type_and_status_choices():
    assert LeaveType.CL == "CL"
    assert LeaveType.RH == "RH"
    assert LeaveType.EL == "EL"
    assert LeaveType.VL == "VL"
    assert LeaveType.COL == "COL"
    assert LeaveType.SCL == "SCL"

    assert LeaveStatus.PENDING_SUBSTITUTE == "PENDING_SUBSTITUTE"
    assert LeaveStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
    assert LeaveStatus.PENDING_HIGHER_APPROVAL == "PENDING_HIGHER_APPROVAL"
    assert LeaveStatus.APPROVED == "APPROVED"
    assert LeaveStatus.REJECTED == "REJECTED"
    assert LeaveStatus.WITHDRAWN == "WITHDRAWN"
    assert LeaveStatus.CANCELLED == "CANCELLED"


def test_calculate_leave_days_half_day():
    d = datetime.date(2026, 11, 2)
    assert calculate_leave_days("CL", d, d, is_half_day=True) == Decimal("0.5")


def test_calculate_leave_days_continuous():
    # Monday to Sunday (7 days total)
    start = datetime.date(2026, 11, 2)  # Monday
    end = datetime.date(2026, 11, 8)    # Sunday
    assert calculate_leave_days(LeaveType.EL, start, end, is_half_day=False) == Decimal("7")
    assert calculate_leave_days(LeaveType.COL, start, end, is_half_day=False) == Decimal("7")
    assert calculate_leave_days(LeaveType.VL, start, end, is_half_day=False) == Decimal("7")


def test_calculate_leave_days_working_days():
    # Monday to Sunday (only 5 working days for CL/RH/SCL)
    start = datetime.date(2026, 11, 2)  # Monday
    end = datetime.date(2026, 11, 8)    # Sunday
    assert calculate_leave_days(LeaveType.CL, start, end, is_half_day=False) == Decimal("5")
    assert calculate_leave_days(LeaveType.RH, start, end, is_half_day=False) == Decimal("5")
    assert calculate_leave_days(LeaveType.SCL, start, end, is_half_day=False) == Decimal("5")


def test_serializer_date_order_validation():
    data = {
        "leave_type": "CL",
        "start_date": datetime.date(2026, 11, 5),
        "end_date": datetime.date(2026, 11, 2),
        "purpose": "Personal reason",
    }
    s = LeaveApplicationCreateSerializer(data=data)
    assert not s.is_valid()
    assert "end_date" in s.errors


def test_serializer_half_day_only_cl():
    data = {
        "leave_type": "EL",
        "start_date": datetime.date(2026, 11, 2),
        "end_date": datetime.date(2026, 11, 2),
        "is_half_day": True,
        "purpose": "Personal reason",
    }
    s = LeaveApplicationCreateSerializer(data=data)
    assert not s.is_valid()
    assert "is_half_day" in s.errors


def test_serializer_half_day_single_date_only():
    data = {
        "leave_type": "CL",
        "start_date": datetime.date(2026, 11, 2),
        "end_date": datetime.date(2026, 11, 3),
        "is_half_day": True,
        "purpose": "Personal reason",
    }
    s = LeaveApplicationCreateSerializer(data=data)
    assert not s.is_valid()
    assert "is_half_day" in s.errors


def test_serializer_station_leave_address_required():
    data = {
        "leave_type": "CL",
        "start_date": datetime.date(2026, 11, 2),
        "end_date": datetime.date(2026, 11, 2),
        "is_station_leave": True,
        "station_address": "   ",
        "purpose": "Going out of Jabalpur",
    }
    s = LeaveApplicationCreateSerializer(data=data)
    assert not s.is_valid()
    assert "station_address" in s.errors


def test_serializer_self_substitute_rejected():
    data = {
        "leave_type": "CL",
        "start_date": datetime.date(2026, 11, 2),
        "end_date": datetime.date(2026, 11, 2),
        "purpose": "Out of office",
        "substitute_user_id": 42,
    }
    mock_request = MagicMock()
    mock_request.principal = SimpleNamespace(user_id=42)
    s = LeaveApplicationCreateSerializer(data=data, context={"request": mock_request})
    assert not s.is_valid()
    assert "substitute_user_id" in s.errors


def test_serializer_valid_submission():
    data = {
        "leave_type": "CL",
        "start_date": datetime.date(2026, 11, 2),
        "end_date": datetime.date(2026, 11, 2),
        "is_half_day": True,
        "purpose": "Medical consultation",
        "substitute_user_id": 99,
    }
    mock_request = MagicMock()
    mock_request.principal = SimpleNamespace(user_id=42)
    s = LeaveApplicationCreateSerializer(data=data, context={"request": mock_request})
    assert s.is_valid(), s.errors
