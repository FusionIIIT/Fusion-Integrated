"""End-to-end service regressions for cancellation, extensions, and year end."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from conftest import make_principal
from modules.leave import contracts
from modules.leave.models import LeaveAccountTransaction, LeaveApplication, LeavePolicy
from modules.leave.services import accounts, applications, year_end

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee():
    return make_principal(
        user_id=101, kind="staff", active_role="staff", roles=("staff",),
        permissions=("leave.application.create", "leave.application.delete"),
    )


@pytest.fixture
def head():
    return make_principal(
        user_id=202, kind="staff", active_role="Unit Head", roles=("Unit Head",),
        permissions=("leave.application.review",),
    )


@pytest.fixture
def sanctioner():
    return make_principal(
        user_id=303, kind="staff", active_role="Sanctioning Authority",
        roles=("Sanctioning Authority",), permissions=("leave.application.approve",),
    )


@pytest.fixture
def approved_cl():
    start = timezone.localdate() + timedelta(days=10)
    row = LeaveApplication.objects.create(
        applicant_user_id=101, request_kind="new", leave_type="CL",
        start_date=start, end_date=start + timedelta(days=2),
        requested_days=Decimal("3"), purpose="Leave",
        status="approved", unit_head_user_id=202,
    )
    accounts.post(
        user_id=101, leave_type="CL", year=start.year, amount=Decimal("20"),
        transaction_type="annual_entitlement", source_key=f"cl-entitlement:{start.year}",
    )
    accounts.post(
        user_id=101, leave_type="CL", year=start.year, amount=Decimal("-3"),
        transaction_type="leave_approved", source_key=f"approved:{row.pk}",
        application=row,
    )
    return row


@pytest.mark.parametrize("outcome,restored", [("approve", True), ("reject", False)])
def test_prestart_cancellation_decision_updates_original_and_ledger(
    employee, head, approved_cl, outcome, restored,
):
    child = applications.request_cancellation(employee, approved_cl)
    assert child.request_kind == "cancellation"
    assert child.status == "cancellation_pending_unit_head_review"
    assert accounts.balance(101, "CL", approved_cl.start_date.year) == Decimal("17")

    decided = applications.act_on_application(
        head, child, event="unit_head_cancel", outcome=outcome,
    )
    approved_cl.refresh_from_db()
    if restored:
        assert decided.status == "cancelled"
        assert approved_cl.status == "cancelled"
        assert accounts.balance(101, "CL", approved_cl.start_date.year) == Decimal("20")
    else:
        assert decided.status == "cancellation_rejected_original_unchanged"
        assert approved_cl.status == "approved"
        assert accounts.balance(101, "CL", approved_cl.start_date.year) == Decimal("17")


def test_cancellation_denies_other_users_and_started_leave(employee, approved_cl):
    outsider = make_principal(user_id=999, permissions=("leave.application.delete",))
    with pytest.raises(NotFound):
        applications.request_cancellation(outsider, approved_cl)
    approved_cl.start_date = timezone.localdate()
    approved_cl.save(update_fields=["start_date"])
    with pytest.raises(ValidationError):
        applications.request_cancellation(employee, approved_cl)


@pytest.fixture
def approved_el(monkeypatch):
    today = timezone.localdate()
    start, end = today - timedelta(days=5), today + timedelta(days=5)
    leave = LeaveApplication.objects.create(
        applicant_user_id=101, request_kind="new", leave_type="EL",
        start_date=start, end_date=end, requested_days=Decimal("11"),
        purpose="Leave", status="approved", unit_head_user_id=202,
        final_authority_user_id=303,
    )
    LeavePolicy.objects.create(
        leave_type="EL", annual_entitlement=Decimal("30"),
        applies_to="all", carry_forward=True, substitute_required=False,
    )
    monkeypatch.setattr(
        applications, "_profile",
        lambda user_id: contracts.EmployeeDTO(
            user_id=user_id, display_name="Test Staff", email="test@example.invalid",
            kind="staff", organizational_unit="CSE",
        ),
    )
    return leave


def test_extension_approval_posts_only_incremental_days(
    employee, head, sanctioner, approved_el,
):
    end = approved_el.end_date + timedelta(days=3)
    child = applications.request_extension(employee, approved_el, end, purpose="Need more time")
    assert child.request_kind == "extension"
    assert child.requested_days == Decimal("3")
    assert child.status == "awaiting_extension_unit_head_review"

    applications.act_on_application(
        head, child, event="unit_head_decision", outcome="recommended",
    )
    decided = applications.act_on_application(
        sanctioner, child, event="sanction", outcome="approve",
    )
    approved_el.refresh_from_db()
    assert decided.status == "extended_incremental_period_posted"
    assert approved_el.end_date == end
    assert approved_el.requested_days == Decimal("14")
    assert accounts.balance(101, "EL", approved_el.start_date.year) == Decimal("27")
    assert LeaveAccountTransaction.objects.filter(
        transaction_type="extension_approved", application=child,
    ).values_list("amount", flat=True).get() == Decimal("-3")


def test_extension_rejects_invalid_period_and_wrong_applicant(employee, approved_el):
    with pytest.raises(ValidationError):
        applications.request_extension(
            employee, approved_el, approved_el.end_date,
        )
    with pytest.raises(NotFound):
        applications.request_extension(
            make_principal(user_id=999), approved_el,
            approved_el.end_date + timedelta(days=3),
        )


def test_year_end_lapse_and_faculty_vl_conversion_are_idempotent(monkeypatch):
    faculty = contracts.EmployeeDTO(
        user_id=501, display_name="Faculty", email="faculty@example.invalid",
        kind="faculty", organizational_unit="CSE",
    )
    monkeypatch.setattr(contracts, "_active_employees", lambda: [faculty])
    LeavePolicy.objects.create(
        leave_type="VL", applies_to="faculty", annual_entitlement=Decimal("20"),
    )
    LeavePolicy.objects.create(
        leave_type="EL", applies_to="all", annual_entitlement=Decimal("0"),
        carry_forward=True,
    )
    LeavePolicy.objects.create(
        leave_type="CL", applies_to="all", annual_entitlement=Decimal("12"),
    )

    result = year_end.process_year_end(2025)

    assert result == {"employees": 1, "transactions": 3}
    assert accounts.balance(501, "VL", 2025) == Decimal("0")
    assert accounts.balance(501, "EL", 2026) == Decimal("10")
    assert accounts.balance(501, "CL", 2025) == Decimal("0")
    tx_count = LeaveAccountTransaction.objects.count()

    again = year_end.process_year_end(2025)

    assert again == {"employees": 1, "transactions": 0}
    assert LeaveAccountTransaction.objects.count() == tx_count
    assert accounts.balance(501, "EL", 2026) == Decimal("10")
