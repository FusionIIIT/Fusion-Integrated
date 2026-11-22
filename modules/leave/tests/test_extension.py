"""Tests for extension of ongoing leave (BR-EL-025, EL-UC-009, WF-EL-04)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.models import LeaveBalance
from modules.leave.services import (
    apply_for_leave,
    request_extension,
    sanction_application,
)


@pytest.mark.django_db
def test_extension_ongoing_el_success():
    user_id = 501
    today = date.today()
    # Ongoing leave: started 2 days ago, ends 2 days from now
    parent_start = today - timedelta(days=2)
    parent_end = today + timedelta(days=2)  # total 5 days (e.g. Nov 2 - Nov 6)

    bal = LeaveBalance.objects.create(
        user_id=user_id, year=parent_start.year, el_balance=Decimal("30.0")
    )
    parent = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=parent_start,
        end_date=parent_end,
        purpose="Medical recovery",
    )
    sanction_application(
        sanctioner_user_id=601,
        application_id=parent.pk,
        decision="approved",
    )
    parent.refresh_from_db()
    assert parent.status == "approved"
    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")

    # Extension starts the day after parent_end
    ext_start = parent_end + timedelta(days=1)
    ext_end = parent_end + timedelta(days=3)  # 3 days incremental

    ext = request_extension(
        user_id=user_id,
        application_id=parent.pk,
        start_date=ext_start,
        end_date=ext_end,
        purpose="Continued doctor recommended rest",
    )
    assert ext.status == "extension_requested"
    assert ext.parent_leave_id == parent.pk
    assert ext.days_count == Decimal("3.0")

    # Sanction extension
    sanction_application(
        sanctioner_user_id=601,
        application_id=ext.pk,
        decision="approved",
    )
    ext.refresh_from_db()
    parent.refresh_from_db()
    bal.refresh_from_db()
    assert ext.status == "approved"
    assert parent.status == "approved"
    assert bal.el_balance == Decimal("22.0")  # 25 - 3 = 22


@pytest.mark.django_db
def test_extension_rejection_preserves_original_approved():
    user_id = 502
    today = date.today()
    parent_start = today - timedelta(days=1)
    parent_end = today + timedelta(days=2)

    bal = LeaveBalance.objects.create(
        user_id=user_id, year=parent_start.year, el_balance=Decimal("30.0")
    )
    parent = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=parent_start,
        end_date=parent_end,
        purpose="Family emergency",
    )
    sanction_application(
        sanctioner_user_id=601,
        application_id=parent.pk,
        decision="approved",
    )
    bal.refresh_from_db()
    assert bal.el_balance == Decimal("26.0")  # 30 - 4 = 26

    ext_start = parent_end + timedelta(days=1)
    ext_end = parent_end + timedelta(days=2)

    ext = request_extension(
        user_id=user_id,
        application_id=parent.pk,
        start_date=ext_start,
        end_date=ext_end,
        purpose="More time needed",
    )

    sanction_application(
        sanctioner_user_id=601,
        application_id=ext.pk,
        decision="rejected",
        remarks="Cannot extend due to project commitments",
    )
    ext.refresh_from_db()
    parent.refresh_from_db()
    bal.refresh_from_db()

    assert ext.status == "rejected"
    assert parent.status == "approved"
    assert bal.el_balance == Decimal("26.0")  # Balance unchanged


@pytest.mark.django_db
def test_extension_fails_for_cl_category():
    user_id = 503
    today = date.today()
    # If today is a weekday, let's create a 1-day CL
    # Or create an approved CL
    LeaveBalance.objects.create(user_id=user_id, year=today.year, cl_balance=Decimal("8.0"))
    # Suppose parent is CL
    parent = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=today,
        end_date=today,
        purpose="CL day",
    )
    parent.status = "approved"
    parent.save()

    with pytest.raises(ConflictError) as exc_info:
        request_extension(
            user_id=user_id,
            application_id=parent.pk,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=2),
            purpose="Extend CL",
        )
    assert exc_info.value.code == "extension_not_allowed"


@pytest.mark.django_db
def test_extension_fails_when_not_consecutive():
    user_id = 504
    today = date.today()
    parent_start = today - timedelta(days=1)
    parent_end = today + timedelta(days=2)

    LeaveBalance.objects.create(user_id=user_id, year=parent_start.year, el_balance=Decimal("30.0"))
    parent = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=parent_start,
        end_date=parent_end,
        purpose="Leave",
    )
    parent.status = "approved"
    parent.save()

    # Gap of 1 day: starts 2 days after parent_end instead of 1
    with pytest.raises(BadRequestError) as exc_info:
        request_extension(
            user_id=user_id,
            application_id=parent.pk,
            start_date=parent_end + timedelta(days=2),
            end_date=parent_end + timedelta(days=4),
            purpose="Non-consecutive extension",
        )
    assert exc_info.value.code == "invalid_extension_period"
