from datetime import date
from decimal import Decimal
from modules.elm.api.views import LeaveApplicationSerializer
from modules.elm.models import LeaveApplication


import pytest
from django.core.exceptions import ValidationError

from modules.elm.models import LeaveApplication


@pytest.mark.django_db
def test_leave_application_defaults_and_fields():
    application = LeaveApplication.objects.create(
        user_id=126,
        leave_type="CL",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("0.5"),
        reason="Personal work",
    )

    assert application.status == "submitted"
    assert application.user_id == 126
    assert application.leave_type == "CL"


def test_leave_application_rejects_end_date_before_start_date():
    application = LeaveApplication(
        user_id=126,
        leave_type="CL",
        start_date=date(2026, 10, 21),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("0.5"),
        reason="Personal work",
    )

    with pytest.raises(ValidationError):
        application.clean()




def test_leave_application_supports_half_day_period_choices():
    assert LeaveApplication.HALF_DAY_PERIODS == [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    application = LeaveApplication(
        user_id=126,
        leave_type="CL",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("0.5"),
        reason="Personal work",
        half_day_period="first_half",
    )

    assert application.half_day_period == "first_half"


@pytest.mark.parametrize("period", ["first_half", "second_half"])
def test_serializer_accepts_valid_half_day_period(period):
    serializer = LeaveApplicationSerializer(
        data={
            "leave_type": "CL",
            "start_date": "2026-10-20",
            "end_date": "2026-10-20",
            "requested_days": "0.5",
            "reason": "Personal work",
            "half_day_period": period,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["half_day_period"] == period


def test_serializer_rejects_invalid_half_day_period():
    serializer = LeaveApplicationSerializer(
        data={
            "leave_type": "CL",
            "start_date": "2026-10-20",
            "end_date": "2026-10-20",
            "requested_days": "0.5",
            "reason": "Personal work",
            "half_day_period": "invalid",
        }
    )

    assert not serializer.is_valid()
    assert "half_day_period" in serializer.errors
