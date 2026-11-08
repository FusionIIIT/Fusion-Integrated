from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveBalance,
    LeaveType,
)
from modules.elm.services.decisions import decide_leave_application

FINAL_AUTHORITY_ID = 900
DECISION_PERMISSION = "elm.leave_application.decide"


class FakePrincipal:
    def __init__(self, user_id, permissions=()):
        self.user_id = user_id
        self.permissions = frozenset(permissions)

    def has_permission(self, code):
        return code in self.permissions


@pytest.fixture
def authorized_actor():
    return FakePrincipal(
        FINAL_AUTHORITY_ID,
        {DECISION_PERMISSION},
    )


@pytest.fixture
def pending_cl_request(db):
    balance = LeaveBalance.objects.create(
        user_id=801,
        leave_type=LeaveType.CL,
        leave_year=2026,
        entitlement=Decimal("8"),
        available_balance=Decimal("8"),
    )

    application = LeaveApplication.objects.create(
        user_id=801,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
        status=LeaveApplicationStatus.PENDING,
        assigned_final_authority_user_id=FINAL_AUTHORITY_ID,
        workflow_stage="awaiting_unit_head_review",
    )

    return application, balance


@pytest.mark.django_db
def test_approval_deducts_balance_and_updates_status(pending_cl_request, authorized_actor):
    application, balance = pending_cl_request

    result = decide_leave_application(
        actor=authorized_actor,
        application_id=application.pk,
        decision=LeaveApplicationStatus.APPROVED,
    )

    balance.refresh_from_db()

    assert result.status == LeaveApplicationStatus.APPROVED
    assert balance.available_balance == Decimal("7")


@pytest.mark.django_db
def test_rejection_does_not_deduct_balance(pending_cl_request, authorized_actor):
    application, balance = pending_cl_request

    result = decide_leave_application(
        actor=authorized_actor,
        application_id=application.pk,
        decision=LeaveApplicationStatus.REJECTED,
    )

    balance.refresh_from_db()

    assert result.status == LeaveApplicationStatus.REJECTED
    assert balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_already_decided_request_cannot_be_decided_again(pending_cl_request, authorized_actor):
    application, balance = pending_cl_request

    decide_leave_application(
        actor=authorized_actor,
        application_id=application.pk,
        decision=LeaveApplicationStatus.REJECTED,
    )

    with pytest.raises(LeaveRuleError, match="Only pending"):
        decide_leave_application(
            actor=authorized_actor,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    balance.refresh_from_db()
    assert balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_invalid_decision_is_rejected(pending_cl_request, authorized_actor):
    application, balance = pending_cl_request

    with pytest.raises(LeaveRuleError, match="Decision must be"):
        decide_leave_application(
            actor=authorized_actor,
            application_id=application.pk,
            decision="withdrawn",
        )

    application.refresh_from_db()
    balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_approval_rejects_insufficient_balance_without_changes(
    pending_cl_request, authorized_actor
):
    application, balance = pending_cl_request

    balance.available_balance = Decimal("0.5")
    balance.save(update_fields=["available_balance", "updated_at"])

    with pytest.raises(LeaveRuleError, match="Insufficient leave balance"):
        decide_leave_application(
            actor=authorized_actor,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    application.refresh_from_db()
    balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert balance.available_balance == Decimal("0.5")


@pytest.mark.django_db
def test_cross_year_approval_does_not_change_balances_if_one_year_is_insufficient(
    authorized_actor,
):
    LeaveBalance.objects.create(
        user_id=802,
        leave_type=LeaveType.EL,
        leave_year=2026,
        entitlement=Decimal("10"),
        available_balance=Decimal("5"),
    )

    second_year_balance = LeaveBalance.objects.create(
        user_id=802,
        leave_type=LeaveType.EL,
        leave_year=2027,
        entitlement=Decimal("10"),
        available_balance=Decimal("0.5"),
    )

    application = LeaveApplication.objects.create(
        user_id=802,
        leave_type=LeaveType.EL,
        start_date=date(2026, 12, 31),
        end_date=date(2027, 1, 1),
        requested_days=Decimal("2"),
        status=LeaveApplicationStatus.PENDING,
        assigned_final_authority_user_id=FINAL_AUTHORITY_ID,
        workflow_stage="awaiting_final_sanction",
    )

    with pytest.raises(LeaveRuleError, match="Insufficient leave balance"):
        decide_leave_application(
            actor=authorized_actor,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    application.refresh_from_db()

    first_year_balance = LeaveBalance.objects.get(
        user_id=802,
        leave_type=LeaveType.EL,
        leave_year=2026,
    )
    second_year_balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert first_year_balance.available_balance == Decimal("5")
    assert second_year_balance.available_balance == Decimal("0.5")


@pytest.mark.django_db
def test_decision_without_actor_is_denied(pending_cl_request):
    application, balance = pending_cl_request

    with pytest.raises(PermissionDeniedError):
        decide_leave_application(
            actor=None,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    application.refresh_from_db()
    balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_actor_without_decision_permission_is_denied(pending_cl_request):
    application, balance = pending_cl_request
    actor = FakePrincipal(FINAL_AUTHORITY_ID)

    with pytest.raises(PermissionDeniedError):
        decide_leave_application(
            actor=actor,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    application.refresh_from_db()
    balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_actor_not_assigned_to_application_is_denied(pending_cl_request):
    application, balance = pending_cl_request
    actor = FakePrincipal(901, {DECISION_PERMISSION})

    with pytest.raises(PermissionDeniedError):
        decide_leave_application(
            actor=actor,
            application_id=application.pk,
            decision=LeaveApplicationStatus.APPROVED,
        )

    application.refresh_from_db()
    balance.refresh_from_db()

    assert application.status == LeaveApplicationStatus.PENDING
    assert balance.available_balance == Decimal("8")
