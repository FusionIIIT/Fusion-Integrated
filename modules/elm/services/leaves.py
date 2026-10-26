"""Database write services for Employee Leave Management (ELM).

Per the Fusion Module Authoring Guide:
- All writes happen through services
- Atomic transactions with select_for_update
- Append-only audit rows (LeaveBalanceTransaction)
- Raises domain errors, never DRF exceptions
"""
from datetime import date, timezone as tz
from decimal import Decimal
from typing import Sequence
from django.db import transaction
from django.utils import timezone

from ..domain import rules, state_machine
from ..domain.entities import LeaveCategory, LeaveStatus, StepDecision, SubstituteStatus
from ..domain.errors import (
    ElmDomainError,
    InsufficientLeaveBalance,
    InvalidLeaveDatesError,
    InvalidSubstituteError,
    InvalidTransition,
    PolicyValidationError,
)
from ..models import (
    ApprovalStep,
    HolidayCalendarEntry,
    LeaveApplication,
    LeaveBalance,
    LeaveBalanceTransaction,
    LeavePolicy,
)


@transaction.atomic
def apply_leave(
    *,
    user_id: int,
    user_role: str,
    category: str,
    leave_start: date,
    leave_end: date,
    purpose: str,
    is_half_day: bool = False,
    half_day: str = "",
    station_leave_required: bool = False,
    station_leave_city: str = "",
    station_leave_purpose: str = "",
    substitute_user_id: int | None = None,
    unit_head_id: int = 2,
    higher_authorities: Sequence[tuple[str, int]] | None = None,
) -> LeaveApplication:
    """Submit a new leave application (CW-EL-01)."""
    # 1. Fetch holiday calendar dates for the year
    year = leave_start.year
    holidays = set(
        HolidayCalendarEntry.objects.filter(year=year).values_list("date", flat=True)
    )

    # 2. Calculate duration
    duration = rules.calculate_duration_days(
        leave_start, leave_end, category, is_half_day, holiday_calendar_dates=holidays
    )
    if duration <= Decimal("0"):
        raise InvalidLeaveDatesError("Calculated leave duration is 0 days.")

    # 3. Check and lock leave balance
    balance_record, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={
            "entitlement": rules.DEFAULT_ENTITLEMENTS.get(category, Decimal("10.0")),
            "balance": rules.DEFAULT_ENTITLEMENTS.get(category, Decimal("10.0")),
            "used": Decimal("0.0"),
            "carried_forward": Decimal("0.0"),
        },
    )
    rules.validate_balance_available(balance_record.balance, duration)

    # 4. Check for overlapping existing leaves (BR-EL-012)
    existing_leaves = list(
        LeaveApplication.objects.filter(
            user_id=user_id,
            status__in=["submitted", "recommended", "not_recommended", "approved"],
        ).values("id", "leave_start", "leave_end", "is_half_day", "half_day", "status")
    )
    rules.validate_no_overlap(
        leave_start, leave_end, is_half_day, half_day, existing_leaves
    )

    # 5. Check substitute eligibility (BR-EL-014)
    substitute_status = SubstituteStatus.NOT_REQUESTED
    if substitute_user_id is not None:
        sub_leaves = list(
            LeaveApplication.objects.filter(
                user_id=substitute_user_id,
                status__in=["submitted", "recommended", "not_recommended", "approved"],
            ).values("id", "leave_start", "leave_end", "status")
        )
        rules.validate_substitute(
            user_id, substitute_user_id, leave_start, leave_end, sub_leaves
        )
        substitute_status = SubstituteStatus.PENDING

    # 6. Create application record
    app = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        status=LeaveStatus.SUBMITTED,
        leave_start=leave_start,
        leave_end=leave_end,
        computed_days=duration,
        is_half_day=is_half_day,
        half_day=half_day,
        purpose=purpose,
        station_leave_required=station_leave_required,
        station_leave_city=station_leave_city,
        station_leave_purpose=station_leave_purpose,
        substitute_user_id=substitute_user_id,
        substitute_status=substitute_status,
    )

    # 7. Deduct balance and record transaction
    balance_record.balance -= duration
    balance_record.used += duration
    balance_record.save(update_fields=["balance", "used", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=category,
        year=year,
        amount=-duration,
        reason="leave_deducted",
        related_application=app,
        reference=f"Applied for #{app.pk}",
        recorded_by_user_id=user_id,
    )

    # 8. Resolve routing and create ApprovalSteps
    is_director = (user_role == "director")
    if is_director:
        # Director self-sanction per BR-EL-020
        app.status = LeaveStatus.APPROVED
        app.save(update_fields=["status", "updated_at"])
        ApprovalStep.objects.create(
            application=app,
            step_order=1,
            assigned_user_id=user_id,
            assigned_role="director",
            step_type="final_decision",
            decision=StepDecision.APPROVED,
            decided_by_user_id=user_id,
            decided_at=timezone.now(),
            comment="Self-sanctioned",
        )
    else:
        steps_meta = rules.resolve_approval_chain(
            category, user_role, user_id, unit_head_id, higher_authorities
        )
        for step in steps_meta:
            ApprovalStep.objects.create(
                application=app,
                step_order=step["step_order"],
                assigned_user_id=step["assigned_user_id"],
                assigned_role=step["assigned_role"],
                step_type=step["step_type"],
                decision=StepDecision.PENDING,
            )

    return app


@transaction.atomic
def respond_to_substitute(
    *, application_id: int, substitute_user_id: int, accept: bool
) -> LeaveApplication:
    """Substitute accepts or declines responsibility (BR-EL-015)."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.substitute_user_id != substitute_user_id:
        raise InvalidSubstituteError("Caller is not the nominated substitute for this request.")
    if app.substitute_status != SubstituteStatus.PENDING:
        raise InvalidTransition(f"Substitute status is already '{app.substitute_status}'.")

    if accept:
        app.substitute_status = SubstituteStatus.ACCEPTED
        app.substitute_noted_at = timezone.now()
    else:
        app.substitute_status = SubstituteStatus.DECLINED
        app.substitute_noted_at = timezone.now()

    app.save(update_fields=["substitute_status", "substitute_noted_at", "updated_at"])
    return app


@transaction.atomic
def withdraw_leave(*, application_id: int, user_id: int) -> LeaveApplication:
    """Withdraw a pending leave request before final approval (BR-EL-022, CW-EL-01).

    Immediate withdrawal restores the deducted balance and marks application withdrawn.
    """
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != user_id:
        raise ElmDomainError("Only the applicant can withdraw this application.")

    if app.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED]:
        raise InvalidTransition(f"Cannot withdraw leave in terminal status '{app.status}'.")

    state_machine.validate_transition(app.status, LeaveStatus.WITHDRAWN)
    app.status = LeaveStatus.WITHDRAWN
    app.save(update_fields=["status", "updated_at"])

    # Restore balance
    year = app.leave_start.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, category=app.category, year=year
    )
    balance.balance += app.computed_days
    balance.used = max(Decimal("0.0"), balance.used - app.computed_days)
    balance.save(update_fields=["balance", "used", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=app.category,
        year=year,
        amount=app.computed_days,
        reason="leave_restored",
        related_application=app,
        reference=f"Withdrawn by applicant",
        recorded_by_user_id=user_id,
    )

    return app


@transaction.atomic
def request_cancellation(*, application_id: int, user_id: int) -> LeaveApplication:
    """Cancel an approved leave before its start date (BR-EL-023, CW-EL-02).

    Approving cancellation marks the leave cancelled and restores deducted balance.
    """
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != user_id:
        raise ElmDomainError("Only the applicant can cancel this leave.")

    if app.status != LeaveStatus.APPROVED:
        raise InvalidTransition("Only approved leave can be cancelled.")

    today = timezone.localdate() if hasattr(timezone, "localdate") else date.today()
    if app.leave_start <= today:
        raise PolicyValidationError("Leave cannot be cancelled on or after its start date.")

    state_machine.validate_transition(LeaveStatus.APPROVED, LeaveStatus.CANCELLED)
    app.status = LeaveStatus.CANCELLED
    app.is_cancellation = True
    app.save(update_fields=["status", "is_cancellation", "updated_at"])

    # Restore balance
    year = app.leave_start.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, category=app.category, year=year
    )
    balance.balance += app.computed_days
    balance.used = max(Decimal("0.0"), balance.used - app.computed_days)
    balance.save(update_fields=["balance", "used", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=app.category,
        year=year,
        amount=app.computed_days,
        reason="cancellation_approved",
        related_application=app,
        reference=f"Cancellation approved for #{app.pk}",
        recorded_by_user_id=user_id,
    )

    return app


@transaction.atomic
def request_extension(
    *,
    original_application_id: int,
    user_id: int,
    extended_end_date: date,
    purpose: str,
) -> LeaveApplication:
    """Extend an ongoing EL/COL/VL leave (BR-EL-025, CW-EL-03)."""
    orig = LeaveApplication.objects.select_for_update().get(pk=original_application_id)
    if orig.user_id != user_id:
        raise ElmDomainError("Only the applicant can extend this leave.")
    if orig.status != LeaveStatus.APPROVED:
        raise InvalidTransition("Only an approved leave can be extended.")
    if orig.category not in [LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL]:
        raise PolicyValidationError("Extensions are only permissible for ongoing EL, COL, or VL.")
    if extended_end_date <= orig.leave_end:
        raise InvalidLeaveDatesError("Extended end date must be after current end date.")

    ext_start = orig.leave_end + timezone.timedelta(days=1)
    duration = rules.calculate_duration_days(ext_start, extended_end_date, orig.category)

    # Balance check
    year = ext_start.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, category=orig.category, year=year
    )
    rules.validate_balance_available(balance.balance, duration)

    ext_app = LeaveApplication.objects.create(
        user_id=user_id,
        category=orig.category,
        status=LeaveStatus.SUBMITTED,
        leave_start=ext_start,
        leave_end=extended_end_date,
        computed_days=duration,
        purpose=purpose,
        is_extension=True,
        extension_of=orig,
    )

    balance.balance -= duration
    balance.used += duration
    balance.save(update_fields=["balance", "used", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=orig.category,
        year=year,
        amount=-duration,
        reason="leave_deducted",
        related_application=ext_app,
        reference=f"Extension for #{orig.pk}",
        recorded_by_user_id=user_id,
    )

    return ext_app


@transaction.atomic
def record_resumption(
    *, application_id: int, user_id: int, actual_resumption_date: date
) -> LeaveApplication:
    """Record employee resumption and adjust balance if early or late (BR-EL-027, 028, CW-EL-04)."""
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    if app.user_id != user_id:
        raise ElmDomainError("Only the applicant can record resumption.")
    if app.status != LeaveStatus.APPROVED:
        raise InvalidTransition("Resumption can only be filed for approved leave.")

    expected_end = app.leave_end
    app.is_resumption = True
    app.actual_resumption_date = actual_resumption_date

    # Compare actual resumption against expected end date
    delta_days = (actual_resumption_date - expected_end).days
    year = app.leave_start.year

    if delta_days != 0:
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=user_id, category=app.category, year=year
        )
        if delta_days < 0:
            # Resumed early: credit back unused days
            unused = Decimal(abs(delta_days))
            balance.balance += unused
            balance.used = max(Decimal("0.0"), balance.used - unused)
            app.computed_days = max(Decimal("0.0"), app.computed_days - unused)
            LeaveBalanceTransaction.objects.create(
                user_id=user_id,
                category=app.category,
                year=year,
                amount=unused,
                reason="resumption_adjusted",
                related_application=app,
                reference=f"Early resumption credit for #{app.pk}",
                recorded_by_user_id=user_id,
            )
        else:
            # Resumed late: deduct extra days
            extra = Decimal(delta_days)
            balance.balance -= extra
            balance.used += extra
            app.computed_days += extra
            LeaveBalanceTransaction.objects.create(
                user_id=user_id,
                category=app.category,
                year=year,
                amount=-extra,
                reason="resumption_adjusted",
                related_application=app,
                reference=f"Late resumption deduction for #{app.pk}",
                recorded_by_user_id=user_id,
            )
        balance.save(update_fields=["balance", "used", "updated_at"])

    app.save(update_fields=["is_resumption", "actual_resumption_date", "computed_days", "updated_at"])
    return app


@transaction.atomic
def record_offline_sanction(
    *,
    user_id: int,
    category: str,
    leave_start: date,
    leave_end: date,
    reference: str,
    sanctioned_by_user_id: int,
) -> LeaveApplication:
    """Synchronize pre-approved offline/paper leave without second approval (BR-EL-029)."""
    duration = rules.calculate_duration_days(leave_start, leave_end, category)
    year = leave_start.year

    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={
            "entitlement": rules.DEFAULT_ENTITLEMENTS.get(category, Decimal("10.0")),
            "balance": rules.DEFAULT_ENTITLEMENTS.get(category, Decimal("10.0")),
            "used": Decimal("0.0"),
            "carried_forward": Decimal("0.0"),
        },
    )
    balance.balance -= duration
    balance.used += duration
    balance.save(update_fields=["balance", "used", "updated_at"])

    app = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        status=LeaveStatus.APPROVED,
        leave_start=leave_start,
        leave_end=leave_end,
        computed_days=duration,
        purpose=f"Offline sanctioned: {reference}",
        is_offline_sanctioned=True,
        offline_sanction_reference=reference,
        offline_sanctioned_by_user_id=sanctioned_by_user_id,
        offline_sanctioned_at=timezone.now(),
    )

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=category,
        year=year,
        amount=-duration,
        reason="offline_sanctioned",
        related_application=app,
        reference=reference,
        recorded_by_user_id=sanctioned_by_user_id,
    )
    return app


@transaction.atomic
def process_approval_step(
    *,
    step_id: int,
    decided_by_user_id: int,
    decision: str,
    comment: str = "",
) -> ApprovalStep:
    """Process an approval step (BR-EL-016–020).

    Valid decisions: 'approved', 'rejected', 'recommended', 'not_recommended'.
    """
    step = ApprovalStep.objects.select_for_update().get(pk=step_id)
    if step.assigned_user_id != decided_by_user_id:
        raise ElmDomainError("User is not authorized for this approval step.")
    if step.decision != StepDecision.PENDING:
        raise InvalidTransition(f"Step has already been decided ({step.decision}).")

    app = LeaveApplication.objects.select_for_update().get(pk=step.application_id)

    # Consent gate check (BR-EL-015): substitute must have accepted if nominated
    if app.substitute_user_id and app.substitute_status != SubstituteStatus.ACCEPTED:
        raise PolicyValidationError("Cannot approve request while substitute consent gate is closed.")

    step.decision = decision
    step.comment = comment
    step.decided_by_user_id = decided_by_user_id
    step.decided_at = timezone.now()
    step.save(update_fields=["decision", "comment", "decided_by_user_id", "decided_at", "updated_at"])

    # Update parent application status
    if step.step_type == "recommendation":
        if decision == "recommended":
            app.status = LeaveStatus.RECOMMENDED
        else:
            app.status = LeaveStatus.NOT_RECOMMENDED
        app.save(update_fields=["status", "updated_at"])

    elif step.step_type == "final_decision":
        if decision == "approved":
            app.status = LeaveStatus.APPROVED
            app.save(update_fields=["status", "updated_at"])
        elif decision == "rejected":
            app.status = LeaveStatus.REJECTED
            app.save(update_fields=["status", "updated_at"])

            # Restore balance on final rejection
            year = app.leave_start.year
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=app.user_id, category=app.category, year=year
            )
            balance.balance += app.computed_days
            balance.used = max(Decimal("0.0"), balance.used - app.computed_days)
            balance.save(update_fields=["balance", "used", "updated_at"])

            LeaveBalanceTransaction.objects.create(
                user_id=app.user_id,
                category=app.category,
                year=year,
                amount=app.computed_days,
                reason="leave_restored",
                related_application=app,
                reference=f"Rejection restored balance for #{app.pk}",
                recorded_by_user_id=decided_by_user_id,
            )

    return step


@transaction.atomic
def convert_faculty_vl_to_el(*, user_id: int, year: int) -> Decimal:
    """Year-end conversion of unused faculty VL to EL at 2 VL : 1 EL (BR-EL-007, 008)."""
    vl_balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, category=LeaveCategory.VL, year=year
    )
    if vl_balance.balance <= Decimal("0.0"):
        return Decimal("0.0")

    unused_vl = vl_balance.balance
    converted_el = rules.convert_vl_to_el(unused_vl)

    # Zero out VL
    vl_balance.balance = Decimal("0.0")
    vl_balance.save(update_fields=["balance", "updated_at"])

    # Credit to EL balance for next year or current year
    el_balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        category=LeaveCategory.EL,
        year=year + 1,
        defaults={
            "entitlement": Decimal("0.0"),
            "balance": Decimal("0.0"),
            "used": Decimal("0.0"),
            "carried_forward": Decimal("0.0"),
        },
    )
    el_balance.balance += converted_el
    el_balance.carried_forward += converted_el
    el_balance.save(update_fields=["balance", "carried_forward", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=LeaveCategory.VL,
        year=year,
        amount=-unused_vl,
        reason="vl_to_el_conversion",
        reference=f"Converted {unused_vl} VL to {converted_el} EL for {year + 1}",
    )
    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        category=LeaveCategory.EL,
        year=year + 1,
        amount=converted_el,
        reason="vl_to_el_conversion",
        reference=f"Converted from {unused_vl} VL in {year}",
    )

    return converted_el
