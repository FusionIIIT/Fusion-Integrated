"""Tests for Employee Leave Management workflow services."""

from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    PermissionDeniedError,
)
from fusion_auth.client import UserRef
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveType,
    SubstituteNomination,
    WorkflowTransition,
)
from modules.leave.services import (
    apply_for_leave,
    respond_to_substitute,
    review_unit_head,
    sanction_leave,
    withdraw_leave_request,
)


@pytest.fixture
def setup_leave_env(db, stub_iam):
    # Setup IAM users via stub_iam keeping modular boundaries intact
    stub_iam(
        users={
            1001: UserRef(
                user_id=1001,
                username="fac_alice",
                display_name="Alice CSE",
                kind="faculty",
                department="Computer Science & Engineering",
            ),
            1002: UserRef(
                user_id=1002,
                username="fac_bob",
                display_name="Bob CSE",
                kind="faculty",
                department="Computer Science & Engineering",
            ),
            2001: UserRef(
                user_id=2001,
                username="hod_cse",
                display_name="Dr. Smith HOD CSE",
                kind="faculty",
                department="Computer Science & Engineering",
            ),
            2002: UserRef(
                user_id=2002,
                username="hod_me",
                display_name="Dr. Taylor HOD ME",
                kind="faculty",
                department="Mechanical Engineering",
            ),
            3001: UserRef(
                user_id=3001,
                username="dean_acad",
                display_name="Prof. Johnson Dean",
                kind="faculty",
                department="Administration",
            ),
            4001: UserRef(
                user_id=4001,
                username="director",
                display_name="Prof. Director",
                kind="faculty",
                department="Directorate",
            ),
        }
    )

    # Setup Leave Types
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        allows_half_day=True,
        lapses_at_year_end=True,
        is_continuous_count=False,
    )
    el = LeaveType.objects.create(
        code="EL",
        name="Earned Leave",
        allows_half_day=False,
        carries_forward=True,
        is_continuous_count=True,
        requires_substitute=True,
    )

    # Setup Balances for 2026
    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("8.0"),
    )
    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=el,
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("30.0"),
    )
    LeaveBalance.objects.create(
        user_id=4001,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("8.0"),
    )

    return {"CL": cl, "EL": el}


@pytest.mark.django_db
def test_apply_for_leave_successful_and_state(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Family personal engagement",
        is_station_leave=True,
        station_destination="Bhopal",
    )
    assert req.status == LeaveState.AWAITING_UNIT_HEAD
    assert req.current_handler_role == "HOD"
    assert req.department == "Computer Science & Engineering"
    assert req.cadre == "faculty"
    assert req.requested_days == Decimal("2.0")
    assert req.station_destination == "Bhopal"
    assert WorkflowTransition.objects.filter(request=req, action="apply").exists()


@pytest.mark.django_db
def test_apply_for_leave_with_substitute(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        reason="Personal rest",
        substitute_user_id=1002,
    )
    assert req.status == LeaveState.AWAITING_SUBSTITUTE
    nomination = SubstituteNomination.objects.get(request=req)
    assert nomination.substitute_user_id == 1002
    assert nomination.status == "pending"


@pytest.mark.django_db
def test_apply_for_leave_insufficient_balance_rejected(setup_leave_env):
    # Try to apply for 10 days of CL when only 8 are available
    with pytest.raises(ConflictError, match="Insufficient leave balance"):
        apply_for_leave(
            actor_user_id=1001,
            leave_type_code="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 13),
            reason="Long leave",
        )


@pytest.mark.django_db
def test_apply_for_leave_overlapping_rejected_with_half_day_exception(setup_leave_env):
    # Apply first half CL on 2026-11-20
    req1 = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 20),
        reason="Morning doctor appointment",
        is_half_day=True,
        half_day_period="first_half",
    )
    assert req1.status == LeaveState.AWAITING_UNIT_HEAD

    # 1. Applying second half on the SAME date should SUCCEED (BR-EL-012 exception)
    req2 = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 20),
        reason="Afternoon bank work",
        is_half_day=True,
        half_day_period="second_half",
    )
    assert req2.status == LeaveState.AWAITING_UNIT_HEAD

    # 2. Applying again for first_half on the same date should FAIL (overlap)
    with pytest.raises(ConflictError, match="overlaps"):
        apply_for_leave(
            actor_user_id=1001,
            leave_type_code="CL",
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 20),
            reason="Duplicate morning leave",
            is_half_day=True,
            half_day_period="first_half",
        )


@pytest.mark.django_db
def test_respond_to_substitute_accept_and_decline(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        reason="Personal rest",
        substitute_user_id=1002,
    )
    nomination = req.substitutes.first()

    # Unauthorized user cannot respond
    with pytest.raises(PermissionDeniedError):
        respond_to_substitute(
            actor_user_id=9999,
            nomination_id=nomination.id,
            decision="accepted",
        )

    # 1. Substitute accepts -> moves to awaiting_unit_head
    nom = respond_to_substitute(
        actor_user_id=1002,
        nomination_id=nomination.id,
        decision="accepted",
        remarks="Glad to cover responsibilities",
    )
    assert nom.status == "accepted"
    req.refresh_from_db()
    assert req.status == LeaveState.AWAITING_UNIT_HEAD
    assert req.current_handler_role == "HOD"

    # Cannot respond again (conflict)
    with pytest.raises(ConflictError):
        respond_to_substitute(
            actor_user_id=1002,
            nomination_id=nomination.id,
            decision="declined",
        )


@pytest.mark.django_db
def test_review_unit_head_cl_final_approval_and_balance_debit(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Family personal engagement",
    )
    assert req.requested_days == Decimal("2.0")

    # 1. Department isolation guard: HOD ME (user 2002) cannot approve CSE request
    with pytest.raises(PermissionDeniedError, match="does not match request department"):
        review_unit_head(
            actor_user_id=2002,
            actor_roles=["HOD"],
            request_id=req.id,
            decision="approve",
        )

    # 2. Self-approval guard: Applicant (user 1001) cannot approve their own request
    with pytest.raises(PermissionDeniedError, match="cannot review their own"):
        review_unit_head(
            actor_user_id=1001,
            actor_roles=["HOD"],
            request_id=req.id,
            decision="approve",
        )

    # 3. HOD CSE (user 2001) approves CL request -> FINAL APPROVAL
    reviewed = review_unit_head(
        actor_user_id=2001,
        actor_roles=["HOD"],
        request_id=req.id,
        decision="approve",
        remarks="Approved by HOD",
    )
    assert reviewed.status == LeaveState.APPROVED

    # Check balance deduction and ledger audit entry
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="CL", year=2026)
    assert bal.available_days == Decimal("6.0")  # 8.0 - 2.0 = 6.0
    assert bal.used_days == Decimal("2.0")

    ledger = LeaveLedgerEntry.objects.get(balance=bal, reference_id=req.id)
    assert ledger.entry_type == "debit"
    assert ledger.amount == Decimal("2.0")
    assert ledger.balance_after == Decimal("6.0")


@pytest.mark.django_db
def test_review_unit_head_higher_sanction_recommendation(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        reason="Research writing",
        substitute_user_id=1002,
    )
    # Substitute accepts first
    respond_to_substitute(
        actor_user_id=1002, nomination_id=req.substitutes.first().id, decision="accepted"
    )
    req.refresh_from_db()

    # Unit Head for EL must use recommend/not_recommend, not approve/reject (BR-EL-017)
    with pytest.raises(BadRequestError):
        review_unit_head(
            actor_user_id=2001,
            actor_roles=["HOD"],
            request_id=req.id,
            decision="approve",
        )

    # Unit Head records recommendation
    reviewed = review_unit_head(
        actor_user_id=2001,
        actor_roles=["HOD"],
        request_id=req.id,
        decision="recommend",
        remarks="Substituted and recommended",
    )
    assert reviewed.status == LeaveState.AWAITING_SANCTION
    assert reviewed.current_handler_role == "Dean Academic"
    assert reviewed.unit_head_recommendation == "recommended"

    # Balance NOT deducted yet (not final approval)
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    assert bal.available_days == Decimal("30.0")


@pytest.mark.django_db
def test_sanction_leave_higher_authority_approval_and_rejection(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        reason="Research writing",
        substitute_user_id=1002,
    )
    respond_to_substitute(
        actor_user_id=1002, nomination_id=req.substitutes.first().id, decision="accepted"
    )
    review_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )
    req.refresh_from_db()

    # Unauthorized role cannot sanction
    with pytest.raises(PermissionDeniedError):
        sanction_leave(
            actor_user_id=1002,
            actor_roles=["faculty"],
            request_id=req.id,
            decision="approve",
        )

    # Dean Academic sanctions leave
    sanctioned = sanction_leave(
        actor_user_id=3001,
        actor_roles=["Dean Academic"],
        request_id=req.id,
        decision="approve",
        remarks="Sanctioned by Dean",
    )
    assert sanctioned.status == LeaveState.APPROVED

    # Check balance deduction
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    assert bal.available_days == Decimal("25.0")  # 30.0 - 5.0 (continuous 10..14 is 5 days)
    assert bal.used_days == Decimal("5.0")
    assert LeaveLedgerEntry.objects.filter(balance=bal, entry_type="debit").exists()


@pytest.mark.django_db
def test_director_self_sanction_path(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=4001,
        leave_type_code="CL",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        reason="Official meeting travel",
        actor_roles=["Director"],
    )
    assert req.status == LeaveState.AWAITING_DIRECTOR

    # Another user cannot self-sanction Director request
    with pytest.raises(PermissionDeniedError):
        sanction_leave(
            actor_user_id=3001,
            actor_roles=["Dean Academic"],
            request_id=req.id,
            decision="approve",
        )

    # Director executes self-sanction (BR-EL-020)
    sanctioned = sanction_leave(
        actor_user_id=4001,
        actor_roles=["Director"],
        request_id=req.id,
        decision="approve",
    )
    assert sanctioned.status == LeaveState.APPROVED


@pytest.mark.django_db
def test_withdraw_leave_request(setup_leave_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 6),
        reason="Trip plan",
    )
    assert req.status == LeaveState.AWAITING_UNIT_HEAD

    # 1. Other user cannot withdraw
    with pytest.raises(PermissionDeniedError):
        withdraw_leave_request(
            actor_user_id=1002,
            request_id=req.id,
        )

    # 2. Applicant withdraws successfully before approval (BR-EL-022)
    withdrawn = withdraw_leave_request(
        actor_user_id=1001,
        request_id=req.id,
        remarks="Trip cancelled",
    )
    assert withdrawn.status == LeaveState.WITHDRAWN
    assert WorkflowTransition.objects.filter(request=req, action="withdraw").exists()

    # 3. Cannot withdraw again or withdraw an approved request
    with pytest.raises(ConflictError):
        withdraw_leave_request(
            actor_user_id=1001,
            request_id=req.id,
        )
