from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.state_machine import WorkflowTransitionError
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveStatus
from modules.elm.services.leave_service import LeaveService


@pytest.fixture
def substitute_employees(db):
    from modules.directory.models import UserRef

    return [
        UserRef.objects.create(
            user_id=user_id,
            username=f"employee{user_id}",
            display_name=f"Employee {user_id}",
            kind="faculty",
        )
        for user_id in (2001, 2002)
    ]


@pytest.mark.django_db
def test_application_uses_configured_entitlement_and_calculates_days():
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="CL",
        year=2026,
        credited=Decimal("12.0"),
    )

    request = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        duration_days=Decimal("3.0"),
        reason="Personal work",
    )

    balance = LeaveBalance.objects.get(user_id="1001", leave_type="CL", year=2026)
    assert request.duration_days == Decimal("3")
    assert request.status == LeaveStatus.PENDING_UNIT_HEAD
    assert balance.pending == Decimal("3.0")


@pytest.mark.django_db
def test_application_rejects_client_duration_mismatch():
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="CL",
        year=2026,
        credited=Decimal("12.0"),
    )

    with pytest.raises(ValueError, match="Duration must match"):
        LeaveService.apply_leave(
            applicant_id="1001",
            leave_type="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
            duration_days=Decimal("1.0"),
            reason="Personal work",
        )


@pytest.mark.django_db
def test_missing_entitlement_does_not_create_a_fabricated_quota():
    with pytest.raises(ValueError, match="No leave entitlement is configured"):
        LeaveService.apply_leave(
            applicant_id="1001",
            leave_type="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            duration_days=Decimal("1.0"),
            reason="Personal work",
        )

    assert not LeaveBalance.objects.filter(user_id="1001", leave_type="CL", year=2026).exists()
    assert LeaveRequest.objects.count() == 0


@pytest.mark.django_db
def test_substitute_decline_allows_replacement_before_approval(substitute_employees):
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="CL",
        year=2026,
        credited=Decimal("12.0"),
    )
    request = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        duration_days=Decimal("1.0"),
        reason="Personal work",
        substitute_id="2001",
    )

    LeaveService.respond_substitute(str(request.pk), "2001", False, "Unavailable")
    request.refresh_from_db()
    assert request.status == LeaveStatus.APPLICANT_ACTION_REQUIRED
    with pytest.raises(WorkflowTransitionError):
        LeaveService.review_unit_head(str(request.pk), "3001", True)

    LeaveService.nominate_replacement(str(request.pk), "1001", "2002")
    LeaveService.respond_substitute(str(request.pk), "2002", True)
    LeaveService.review_unit_head(str(request.pk), "3001", True)

    request.refresh_from_db()
    balance = LeaveBalance.objects.get(user_id="1001", leave_type="CL", year=2026)
    assert request.status == LeaveStatus.APPROVED
    assert request.substitute_user_id == "2002"
    assert balance.pending == Decimal("0.0")
    assert balance.availed == Decimal("1.0")


@pytest.mark.django_db
def test_withdrawal_releases_reserved_balance_once():
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="CL",
        year=2026,
        credited=Decimal("12.0"),
    )
    request = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        duration_days=Decimal("1.0"),
        reason="Personal work",
    )

    LeaveService.withdraw_leave(str(request.pk), "1001", "Plans changed")
    with pytest.raises(WorkflowTransitionError):
        LeaveService.withdraw_leave(str(request.pk), "1001", "Repeat")

    balance = LeaveBalance.objects.get(user_id="1001", leave_type="CL", year=2026)
    assert balance.pending == Decimal("0.0")


@pytest.mark.django_db
def test_opposite_half_day_cl_sessions_do_not_overlap():
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="CL",
        year=2026,
        credited=Decimal("2.0"),
    )
    first = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        duration_days=Decimal("0.5"),
        reason="Morning appointment",
        is_half_day=True,
        half_day_session="FN",
    )
    second = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        duration_days=Decimal("0.5"),
        reason="Afternoon appointment",
        is_half_day=True,
        half_day_session="AN",
    )

    assert first.duration_days == second.duration_days == Decimal("0.5")


@pytest.mark.django_db
def test_not_recommended_higher_sanction_request_continues_to_authority():
    LeaveBalance.objects.create(
        user_id="1001",
        leave_type="EL",
        year=2026,
        credited=Decimal("10.0"),
    )
    request = LeaveService.apply_leave(
        applicant_id="1001",
        leave_type="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        duration_days=Decimal("2.0"),
        reason="Personal work",
    )

    LeaveService.review_unit_head(str(request.pk), "3001", False, "Insufficient coverage", True)
    request.refresh_from_db()
    assert request.status == LeaveStatus.PENDING_AUTHORITY
    assert request.rejection_reason == ""
    assert request.action_logs.get(action="NOT_RECOMMEND")

    LeaveService.decide_authority(str(request.pk), "4001", False, "Not sanctioned")
    request.refresh_from_db()
    balance = LeaveBalance.objects.get(user_id="1001", leave_type="EL", year=2026)
    assert request.status == LeaveStatus.REJECTED
    assert balance.pending == Decimal("0.0")


@pytest.mark.django_db
def test_admin_entitlement_adjustment_is_audited_and_preserves_commitments():
    from modules.elm.models import LeaveBalanceAdjustment

    LeaveBalance.objects.create(
        user_id="1001", leave_type="EL", year=2026,
        credited=Decimal("10.0"), availed=Decimal("2.0"), pending=Decimal("1.0"),
    )

    balance = LeaveService.adjust_entitlement(
        user_id="1001", leave_type="EL", year=2026,
        credited=Decimal("15.0"), actor_id="9001", reason="Approved annual credit",
    )

    adjustment = LeaveBalanceAdjustment.objects.get(user_id="1001")
    assert balance.balance == Decimal("12.0")
    assert adjustment.previous_credited == Decimal("10.0")
    assert adjustment.credited == Decimal("15.0")

    with pytest.raises(ValueError, match="lower than already used or reserved"):
        LeaveService.adjust_entitlement(
            user_id="1001", leave_type="EL", year=2026,
            credited=Decimal("2.0"), actor_id="9001", reason="Invalid reduction",
        )
