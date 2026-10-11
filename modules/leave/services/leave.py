"""Leave services — all writes.

Key invariants:
  - Only employed users may apply (checked via hr.contracts).
  - Balance is checked at application time; deducted on approval.
  - Every status change writes an append-only LeaveRequestTransition.
  - select_for_update on the balance row prevents double-booking.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveRequestTransition,
    LeaveType,
)
from modules.leave.selectors import leave as selectors

log = logging.getLogger("fusion.leave.services")


def _count_days(start: datetime.date, end: datetime.date,
                half_day: str | None) -> float:
    delta = (end - start).days + 1
    if half_day and delta == 1:
        return 0.5
    return float(delta)


def _resolve_or_raise(frm: str, to: str, actor_kind: str):
    try:
        return sm.resolve(frm, to, actor_kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A leave request cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
            details=[{
                "from": exc.frm, "to": exc.to,
                "allowed": sm.allowed_targets(exc.frm, actor_kind),
            }],
        ) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": exc.frm, "to": exc.to, "actor": exc.actor_kind}],
        ) from exc


@transaction.atomic
def create_leave_type(
    *,
    code: str,
    name: str,
    annual_quota: int = 0,
    max_carry_forward: int = 0,
    allow_half_day: bool = False,
    requires_doc_after_days: int | None = None,
    actor_user_id: int,
) -> LeaveType:
    if LeaveType.objects.filter(code=code).exists():
        raise ConflictError(
            f"A leave type with code '{code}' already exists.",
            code="leave_type_code_taken",
        )
    lt = LeaveType.objects.create(
        code=code, name=name,
        annual_quota=annual_quota,
        max_carry_forward=max_carry_forward,
        allow_half_day=allow_half_day,
        requires_doc_after_days=requires_doc_after_days,
        created_by_user_id=actor_user_id,
    )
    log.info("leave.type.created type=%d by=%d", lt.pk, actor_user_id)
    return lt


@transaction.atomic
def credit_balance(
    *,
    user_id: int,
    leave_type_id: int,
    year: int,
    days: float,
    actor_user_id: int,
) -> LeaveBalance:
    lt = selectors.leave_type_by_id(leave_type_id)
    if lt is None:
        raise NotFoundError("Leave type not found.")
    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id, leave_type_id=leave_type_id, year=year,
        defaults={"credited": 0, "used": 0},
    )
    balance.credited += Decimal(str(days))
    balance.save(update_fields=["credited", "updated_at"])
    log.info("leave.balance.credited user=%d type=%d year=%d days=%s by=%d",
             user_id, leave_type_id, year, days, actor_user_id)
    return balance


@transaction.atomic
def apply_for_leave(
    *,
    actor,
    leave_type_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str = "",
    half_day: str | None = None,
) -> LeaveRequest:
    from modules.hr.contracts import get_employments

    emp = get_employments([actor.user_id]).get(actor.user_id)
    if emp is None or not emp.is_employed:
        raise ConflictError(
            "Only employed users may apply for leave.",
            code="not_employed",
        )

    if end_date < start_date:
        raise ConflictError("End date must be on or after start date.",
                            code="dates_invalid")

    lt = selectors.leave_type_by_id(leave_type_id)
    if lt is None:
        raise NotFoundError("Leave type not found.")

    if half_day and not lt.allow_half_day:
        raise ConflictError(
            f"Half-day leave is not permitted for {lt.code}.",
            code="half_day_not_allowed",
        )

    days = _count_days(start_date, end_date, half_day)

    year = start_date.year
    balance = selectors.balance_for_user_and_type(actor.user_id, lt.pk, year)
    remaining = float(balance.remaining) if balance else 0.0
    if remaining < days:
        raise ConflictError(
            f"Insufficient {lt.code} balance: {remaining:.1f} day(s) remaining, "
            f"{days:.1f} requested.",
            code="insufficient_balance",
        )

    req = LeaveRequest.objects.create(
        user_id=actor.user_id,
        leave_type=lt,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        days_requested=Decimal(str(days)),
        reason=reason,
        status=sm.PENDING,
        applied_at=timezone.now(),
    )
    LeaveRequestTransition.objects.create(
        request=req,
        from_status="",
        to_status=sm.PENDING,
        actor_user_id=actor.user_id,
    )
    log.info("leave.request.applied req=%d user=%d type=%d days=%s",
             req.pk, actor.user_id, lt.pk, days)
    return req


@transaction.atomic
def transition(
    *,
    request_id: int,
    to_status: str,
    actor,
    reason: str = "",
) -> LeaveRequest:
    req = (
        LeaveRequest.objects.select_for_update()
        .select_related("leave_type")
        .filter(pk=request_id).first()
    )
    if req is None:
        raise NotFoundError("Leave request not found.")

    if actor.has_permission("leave.request.approve"):
        actor_kind = sm.APPROVER
    else:
        if req.user_id != actor.user_id:
            raise PermissionDeniedError(
                "You may only cancel your own leave requests.",
                code="not_owner",
            )
        actor_kind = sm.REQUESTER

    t = _resolve_or_raise(req.status, to_status, actor_kind)

    if "has_reason" in t.guards and not (reason or "").strip():
        raise ConflictError("A reason is required for this decision.",
                            code="reason_required")

    was_approved = req.status == sm.APPROVED
    frm = req.status
    req.status = to_status

    touched = ["status", "updated_at"]
    if to_status in (sm.APPROVED, sm.REJECTED, sm.REVOKED):
        req.approved_by_user_id = actor.user_id
        req.decided_at = timezone.now()
        req.decision_note = reason[:300]
        touched += ["approved_by_user_id", "decided_at", "decision_note"]

    req.save(update_fields=touched)

    year = req.start_date.year
    if to_status == sm.APPROVED:
        _deduct_balance(req.user_id, req.leave_type_id, year,
                        float(req.days_requested), actor.user_id)

    elif to_status in (sm.CANCELLED, sm.REVOKED) and was_approved:
        _restore_balance(req.user_id, req.leave_type_id, year,
                         float(req.days_requested), actor.user_id)

    LeaveRequestTransition.objects.create(
        request=req, from_status=frm, to_status=to_status,
        actor_user_id=actor.user_id, reason=reason,
    )
    log.info("leave.request.%s req=%d by=%d", to_status, req.pk, actor.user_id)
    return req


def _deduct_balance(user_id: int, leave_type_id: int, year: int,
                    days: float, actor_user_id: int) -> None:
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, leave_type_id=leave_type_id, year=year)
        .first()
    )
    if balance is None:
        raise ConflictError("No leave balance record found; credit balance first.",
                            code="balance_missing")
    d = Decimal(str(days))
    if balance.remaining < d:
        raise ConflictError(
            f"Insufficient balance at approval time: "
            f"{float(balance.remaining):.1f} remaining, {days:.1f} needed.",
            code="insufficient_balance",
        )
    balance.used += d
    balance.save(update_fields=["used", "updated_at"])


def _restore_balance(user_id: int, leave_type_id: int, year: int,
                     days: float, actor_user_id: int) -> None:
    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, leave_type_id=leave_type_id, year=year)
        .first()
    )
    if balance is not None:
        d = Decimal(str(days))
        balance.used = max(Decimal("0"), balance.used - d)
        balance.save(update_fields=["used", "updated_at"])
