"""Entitlement provisioning through the leave-request service."""
from datetime import date

import pytest

from modules.leave.models import (
    AcademicVacationPeriod,
    HolidayCalendar,
    LeaveAccount,
    LeaveHierarchyConfig,
    LeavePolicyConfig,
)
from modules.leave.services.leave_services import submit_leave_request

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("category", "employee_type", "expected_balance"),
    [
        ("CL", "staff", 8.0),
        ("RH", "staff", 2.0),
        ("SCL", "staff", 15.0),
        ("EL", "staff", 30.0),
        ("COL", "staff", 20.0),
        ("VL", "faculty", 60.0),
    ],
)
def test_new_leave_account_uses_baseline_entitlement(
    category, employee_type, expected_balance
):
    day = date(2026, 4, 6)
    role = employee_type
    LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role=role, category=category,
        unit_head_id="hod-cse",
        sanctioning_authority_id="dean-cse" if category not in ("CL", "RH") else "",
    )
    if category == "RH":
        HolidayCalendar.objects.create(
            date=day, title="Restricted holiday", is_restricted_holiday=True
        )
    if category == "VL":
        AcademicVacationPeriod.objects.create(
            title="Institute vacation", start_date=day, end_date=day
        )

    request = submit_leave_request(
        applicant_id=f"new-{category}-{employee_type}",
        applicant_role=employee_type,
        category=category,
        start_date=day,
        end_date=day,
        purpose="Entitlement provisioning test",
    )

    assert request.chargeable_days == 1.0
    account = LeaveAccount.objects.get(
        user_id=f"new-{category}-{employee_type}", category=category, year=2026
    )
    assert account.balance == expected_balance


def test_new_account_uses_current_configured_entitlement():
    day = date(2026, 4, 6)
    LeavePolicyConfig.objects.create(category="CL", annual_entitlement=12.0)
    LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role="staff", category="CL",
        unit_head_id="hod-cse",
    )

    submit_leave_request(
        applicant_id="configured-policy-user",
        applicant_role="staff",
        category="CL",
        start_date=day,
        end_date=day,
        purpose="Configured entitlement test",
    )

    account = LeaveAccount.objects.get(
        user_id="configured-policy-user", category="CL", year=2026
    )
    assert account.balance == 12.0
