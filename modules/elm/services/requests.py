"""Transactional ELM application services.

All policy-sensitive validation is centralized here so alternate API clients
cannot bypass leave rules. User identities remain integer references owned by IAM.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from modules.elm.models import (
    LeaveAccount,
    LeaveBalanceTransaction,
    LeaveCalendarDay,
    LeaveCancellationRequest,
    LeaveRequest,
    LeaveRequestTransition,
    LeaveTypePolicy,
)

HALF = Decimal("0.50")
ONE = Decimal("1.00")


def _calendar_days(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def calculate_requested_days(*, policy: LeaveTypePolicy, start_date: date,
                             end_date: date, start_session: str,
                             end_session: str) -> Decimal:
    """Calculate days from policy; never accept a client-computed total.

    EL/COL/VL are continuous calendar-day leave. CL/SCL/RH count working days,
    excluding weekends and currently published closed holidays. Same-day
    first-half and second-half requests each consume 0.5 day.
    """
    if end_date < start_date:
        raise ValidationError({"end_date": "End date must not precede start date."})
    valid_sessions = dict(LeaveRequest.SESSION_CHOICES)
    if start_session not in valid_sessions or end_session not in valid_sessions:
        raise ValidationError({"session": "Unsupported leave session."})
    if start_date == end_date:
        if start_session == "full" and end_session == "full":
            return ONE
        if start_session == "full" or end_session == "full":
            raise ValidationError({"session": "For a single day, start and end sessions must match."})
        # first-half through second-half is a full day; identical half sessions
        # represent one half-day application.
        return ONE if start_session != end_session else HALF
    continuous = policy.continuous_calendar_days or policy.code in {
        LeaveTypePolicy.EL, LeaveTypePolicy.COL, LeaveTypePolicy.VL
    }
    if continuous:
        days = Decimal((end_date - start_date).days + 1)
        if start_session == "second_half":
            days -= HALF
        if end_session == "first_half":
            days -= HALF
        return days.quantize(HALF)

    closed_dates = set(LeaveCalendarDay.objects.filter(
        date__gte=start_date, date__lte=end_date,
        day_type=LeaveCalendarDay.CLOSED_HOLIDAY, published=True,
    ).values_list("date", flat=True))
    total = Decimal("0.00")
    for current in _calendar_days(start_date, end_date):
        if current.weekday() >= 5 or current in closed_dates:
            continue
        if current == start_date and start_session != "full":
            total += HALF
        elif current == end_date and end_session != "full":
            total += HALF
        else:
            total += ONE
    return total.quantize(HALF)


def _validate_rh_day(*, policy: LeaveTypePolicy, start_date: date,
                     end_date: date):
    if policy.code != LeaveTypePolicy.RH:
        return
    if start_date != end_date:
        raise ValidationError({"end_date": "Restricted Holiday must be a single calendar day."})
    valid = LeaveCalendarDay.objects.filter(
        date=start_date, day_type=LeaveCalendarDay.RH_DAY, published=True,
    ).filter(Q(effective_from__isnull=True) | Q(effective_from__lte=start_date)).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=start_date)
    ).exists()
    if not valid:
        raise ValidationError({"start_date": "Select a date on the effective published Restricted Holiday calendar."})


def _check_overlap(*, user_id: int, start_date: date, end_date: date,
                   start_session: str, end_session: str):
    overlapping = LeaveRequest.objects.filter(
        user_id=user_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
        status__in=[LeaveRequest.PENDING_UNIT_HEAD, LeaveRequest.PENDING_HIERARCHY,
                    LeaveRequest.APPROVED, LeaveRequest.CANCELLATION_PENDING],
    )
    for existing in overlapping:
        if start_date == end_date == existing.start_date == existing.end_date:
            sessions = {start_session, end_session}
            existing_sessions = {existing.start_session, existing.end_session}
            if sessions == {"first_half"} and existing_sessions == {"second_half"}:
                continue
            if sessions == {"second_half"} and existing_sessions == {"first_half"}:
                continue
        raise ValidationError({"start_date": f"The requested period overlaps leave request {existing.pk}."})


@transaction.atomic
def submit_leave_request(*, actor, leave_type_id: int, start_date: date, end_date: date,
                         start_session: str, end_session: str, requested_days=None,
                         reason: str, employee_category: str = "any",
                         substitute_user_id=None) -> LeaveRequest:
    """Create a request after eligibility, calendar, overlap and balance checks."""
    if requested_days is not None and Decimal(str(requested_days)) <= 0:
        raise ValidationError({"requested_days": "Requested days must be greater than zero."})
    if not reason or not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    if start_date.year != end_date.year:
        raise ValidationError({"dates": "Cross-year leave requests are not enabled until yearly balance allocation is configured."})
    if len(reason.strip()) > 2000:
        raise ValidationError({"reason": "Reason must be at most 2000 characters."})
    policy = LeaveTypePolicy.objects.select_for_update().filter(pk=leave_type_id, is_active=True).first()
    if policy is None:
        raise ValidationError({"leave_type": "Unknown or inactive leave type."})
    if policy.employee_category not in ("any", employee_category):
        raise ValidationError({"leave_type": "This leave type is not available for this employee category."})
    _validate_rh_day(policy=policy, start_date=start_date, end_date=end_date)
    days = calculate_requested_days(
        policy=policy, start_date=start_date, end_date=end_date,
        start_session=start_session, end_session=end_session,
    )
    if days <= 0:
        raise ValidationError({"dates": "The selected period contains no eligible leave days."})
    _check_overlap(user_id=actor.user_id, start_date=start_date, end_date=end_date,
                   start_session=start_session, end_session=end_session)

    current_year = start_date.year
    account = LeaveAccount.objects.select_for_update().filter(
        user_id=actor.user_id, leave_type=policy, leave_year=current_year
    ).first()
    if account is None:
        raise ValidationError({"balance": "No leave balance account is configured for this leave type and year."})
    # Pending applications reserve available balance. Calculate in Python to
    # keep cross-year periods explicit and avoid trusting submitted totals.
    reserved_days = Decimal("0.00")
    # Approved leave has already been debited from LeaveAccount.balance_days.
    # Only pending requests reserve balance here; counting approved requests
    # again would double-subtract them and reject valid future applications.
    reservations = LeaveRequest.objects.filter(
        user_id=actor.user_id, leave_type=policy,
        status__in=[LeaveRequest.PENDING_UNIT_HEAD, LeaveRequest.PENDING_HIERARCHY],
        start_date__year=current_year,
    )
    for item in reservations:
        reserved_days += item.requested_days
    if account.balance_days - reserved_days < days:
        raise ValidationError({"balance": "Insufficient available leave balance."})

    if substitute_user_id is not None:
        if substitute_user_id == actor.user_id:
            raise ValidationError({"substitute_user_id": "You cannot nominate yourself as substitute."})
        substitute_overlap = LeaveRequest.objects.filter(
            user_id=substitute_user_id, start_date__lte=end_date, end_date__gte=start_date,
            status__in=[LeaveRequest.PENDING_UNIT_HEAD, LeaveRequest.PENDING_HIERARCHY,
                        LeaveRequest.APPROVED, LeaveRequest.CANCELLATION_PENDING],
        ).exists()
        if substitute_overlap:
            raise ValidationError({"substitute_user_id": "The substitute has overlapping leave during this period."})

    row = LeaveRequest.objects.create(
        user_id=actor.user_id,
        employee_category=employee_category,
        leave_type=policy,
        start_date=start_date,
        end_date=end_date,
        start_session=start_session,
        end_session=end_session,
        requested_days=days,
        reason=reason.strip(),
        substitute_user_id=substitute_user_id,
        substitute_consent="awaiting" if substitute_user_id else "not_required",
        status=LeaveRequest.PENDING_UNIT_HEAD,
    )
    LeaveRequestTransition.objects.create(
        request=row, from_status="", to_status=row.status,
        actor_user_id=actor.user_id, action="submitted", reason="Leave request submitted",
    )
    return row


@transaction.atomic
def respond_to_substitute(*, actor, request_id: int, accept: bool) -> LeaveRequest:
    row = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
    if row is None:
        raise NotFound("Leave request not found.")
    if row.substitute_user_id != actor.user_id:
        raise PermissionDenied("Only the nominated substitute can respond.")
    if row.status != LeaveRequest.PENDING_UNIT_HEAD or row.substitute_consent != "awaiting":
        raise ValidationError("Substitute consent is no longer pending.")
    old = row.status
    row.substitute_consent = "accepted" if accept else "declined"
    if not accept:
        row.status = LeaveRequest.WITHDRAWN
    row.save(update_fields=["substitute_consent", "status", "updated_at"])
    LeaveRequestTransition.objects.create(
        request=row, from_status=old, to_status=row.status,
        actor_user_id=actor.user_id, action="substitute_accepted" if accept else "substitute_declined",
        reason="Substitute consent recorded",
    )
    return row


@transaction.atomic
def withdraw_leave_request(*, actor, request_id: int, reason: str = "") -> LeaveRequest:
    row = LeaveRequest.objects.select_for_update().filter(pk=request_id, user_id=actor.user_id).first()
    if row is None:
        raise NotFound("Leave request not found.")
    if row.status not in (LeaveRequest.PENDING_UNIT_HEAD, LeaveRequest.PENDING_HIERARCHY):
        raise ValidationError("Only pending requests can be withdrawn; submitted requests cannot be edited.")
    old = row.status
    row.status = LeaveRequest.WITHDRAWN
    row.save(update_fields=["status", "updated_at"])
    LeaveRequestTransition.objects.create(
        request=row, from_status=old, to_status=row.status, actor_user_id=actor.user_id,
        action="withdrawn", reason=reason.strip()[:1000],
    )
    return row


@transaction.atomic
def decide_leave_request(*, actor, request_id: int, decision: str, reason: str = "") -> LeaveRequest:
    """Unit Head recommends SCL/EL/COL/VL; finalizes CL/RH or hierarchy stage.

    Caller must have the appropriate IAM permission and role grant. This service
    enforces legal state transitions but intentionally does not invent hierarchy
    routing: the current Fusion IAM/workflow configuration is the authority.
    """
    allowed = {"recommend", "not_recommend", "approve", "reject"}
    if decision not in allowed:
        raise ValidationError({"decision": "Unsupported decision."})
    row = LeaveRequest.objects.select_for_update().select_related("leave_type").filter(pk=request_id).first()
    if row is None:
        raise NotFound("Leave request not found.")
    if row.substitute_consent == "awaiting":
        raise ValidationError("Approval cannot continue before substitute consent is recorded.")
    policy = row.leave_type
    if row.status == LeaveRequest.PENDING_UNIT_HEAD:
        if policy.code in (LeaveTypePolicy.CL, LeaveTypePolicy.RH):
            if decision not in ("approve", "reject"):
                raise ValidationError("CL and RH require a final Unit Head decision.")
            new_status = LeaveRequest.APPROVED if decision == "approve" else LeaveRequest.REJECTED
        else:
            if decision not in ("recommend", "not_recommend"):
                raise ValidationError("This leave type requires a Unit Head recommendation before final sanction.")
            new_status = LeaveRequest.PENDING_HIERARCHY if decision == "recommend" else LeaveRequest.REJECTED
    elif row.status == LeaveRequest.PENDING_HIERARCHY:
        if decision not in ("approve", "reject"):
            raise ValidationError("The configured hierarchy must make the final sanction decision.")
        new_status = LeaveRequest.APPROVED if decision == "approve" else LeaveRequest.REJECTED
    else:
        raise ValidationError("This request is not awaiting a decision.")

    old_status = row.status
    row.status = new_status
    row.decided_at = timezone.now() if new_status in (LeaveRequest.APPROVED, LeaveRequest.REJECTED) else None
    row.save(update_fields=["status", "decided_at", "updated_at"])
    if new_status == LeaveRequest.APPROVED:
        account = LeaveAccount.objects.select_for_update().filter(
            user_id=row.user_id, leave_type=row.leave_type, leave_year=row.start_date.year
        ).first()
        if account is None or account.balance_days < row.requested_days:
            raise ValidationError("Insufficient configured balance at approval time.")
        account.balance_days -= row.requested_days
        account.save(update_fields=["balance_days", "updated_at"])
        LeaveBalanceTransaction.objects.create(
            account=account, request=row, transaction_type=LeaveBalanceTransaction.DEBIT,
            amount_days=row.requested_days, reason="Approved leave debit",
            actor_user_id=actor.user_id, idempotency_key=f"leave-approval:{row.pk}",
        )
    LeaveRequestTransition.objects.create(
        request=row, from_status=old_status, to_status=new_status,
        actor_user_id=actor.user_id, action=decision, reason=reason.strip()[:1000],
    )
    return row

@transaction.atomic
def request_leave_cancellation(*, actor, request_id: int, reason: str):
    """Request cancellation of an approved leave application."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "A cancellation reason is required."})
    if len(reason) > 1000:
        raise ValidationError({"reason": "Reason must be at most 1000 characters."})

    row = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, user_id=actor.user_id
    ).first()
    if row is None:
        raise NotFound("Leave request not found.")
    if row.status != LeaveRequest.APPROVED:
        raise ValidationError("Only approved leave can be submitted for cancellation.")

    if LeaveCancellationRequest.objects.filter(
        leave_request=row, status=LeaveCancellationRequest.PENDING
    ).exists():
        raise ValidationError("A cancellation request is already pending.")

    cancellation = LeaveCancellationRequest.objects.create(
        leave_request=row,
        requested_by_user_id=actor.user_id,
        reason=reason,
    )

    old_status = row.status
    row.status = LeaveRequest.CANCELLATION_PENDING
    row.save(update_fields=["status", "updated_at"])

    LeaveRequestTransition.objects.create(
        request=row,
        from_status=old_status,
        to_status=row.status,
        actor_user_id=actor.user_id,
        action="cancellation_requested",
        reason=reason,
    )
    return cancellation


@transaction.atomic
def decide_leave_cancellation(
    *, actor, cancellation_id: int, decision: str, reason: str = ""
):
    """Approve or reject a cancellation; restore balance only once."""
    if decision not in ("approve", "reject"):
        raise ValidationError({"decision": "Decision must be approve or reject."})
    if not isinstance(reason, str):
        raise ValidationError({"reason": "Reason must be a string."})

    cancellation = (
        LeaveCancellationRequest.objects.select_for_update()
        .select_related("leave_request")
        .filter(pk=cancellation_id)
        .first()
    )
    if cancellation is None:
        raise NotFound("Cancellation request not found.")
    if cancellation.status != LeaveCancellationRequest.PENDING:
        raise ValidationError("This cancellation request has already been decided.")

    row = LeaveRequest.objects.select_for_update().select_related(
        "leave_type"
    ).get(pk=cancellation.leave_request_id)

    if row.status != LeaveRequest.CANCELLATION_PENDING:
        raise ValidationError("The leave request is no longer awaiting cancellation.")

    old_status = row.status
    now = timezone.now()
    cancellation.status = (
        LeaveCancellationRequest.APPROVED
        if decision == "approve"
        else LeaveCancellationRequest.REJECTED
    )
    cancellation.decided_by_user_id = actor.user_id
    cancellation.decided_at = now
    cancellation.save(
        update_fields=[
            "status", "decided_by_user_id", "decided_at", "updated_at"
        ]
    )

    if decision == "approve":
        account = LeaveAccount.objects.select_for_update().filter(
            user_id=row.user_id,
            leave_type=row.leave_type,
            leave_year=row.start_date.year,
        ).first()
        if account is None:
            raise ValidationError("No leave balance account exists for this request.")

        # The unique key protects against accidentally reversing the same
        # approved leave twice.
        reversal_key = f"leave-cancellation:{cancellation.pk}"
        if LeaveBalanceTransaction.objects.filter(
            idempotency_key=reversal_key
        ).exists():
            raise ValidationError("This cancellation has already reversed the balance.")

        account.balance_days += row.requested_days
        account.save(update_fields=["balance_days", "updated_at"])

        LeaveBalanceTransaction.objects.create(
            account=account,
            request=row,
            transaction_type=LeaveBalanceTransaction.REVERSAL,
            amount_days=row.requested_days,
            reason=f"Approved leave cancellation: {cancellation.reason}",
            actor_user_id=actor.user_id,
            idempotency_key=reversal_key,
        )
        row.status = LeaveRequest.CANCELLED
    else:
        row.status = LeaveRequest.APPROVED

    row.save(update_fields=["status", "updated_at"])
    LeaveRequestTransition.objects.create(
        request=row,
        from_status=old_status,
        to_status=row.status,
        actor_user_id=actor.user_id,
        action=f"cancellation_{decision}",
        reason=(reason.strip() or cancellation.reason)[:1000],
    )
    return cancellation