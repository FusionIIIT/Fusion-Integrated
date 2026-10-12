from datetime import date
from decimal import Decimal

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