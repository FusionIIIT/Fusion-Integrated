"""All writes to a leave request. Raises domain errors, not DRF."""
from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import entitlement as ent
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveTransition
from modules.leave.selectors import leaves as scoping


def actor_kind(actor, req: LeaveRequest | None = None) -> str:
    if actor is None:
        return sm.SYSTEM
    if getattr(actor, "has_permission", None):
        if actor.has_permission("elm.leave.self_sanction"):
            return sm.DIRECTOR
        if actor.has_permission("elm.leave.decide"):
            return sm.AUTHORITY
        if actor.has_permission("elm.leave.verify"):
            return sm.ESTABLISHMENT
        if actor.has_permission("elm.leave.recommend"):
            return sm.UNITHEAD

    user_id = getattr(actor, "user_id", None)
    if req is not None and user_id is not None and req.substitute_user_id == user_id:
        return sm.SUBSTITUTE
    return sm.EMPLOYEE


def resolve_or_raise(frm: str, to: str, kind: str):
    try:
        return sm.resolve(frm, to, kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A leave cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
        ) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            f"Your role ({exc.actor_kind}) cannot do this step from '{exc.frm}' to '{exc.to}'."
        ) from exc


def get_or_create_balance(user_id: int, year: int, category: str) -> LeaveBalance:
    """Retrieve or initialize the leave balance for an employee (BR-EL-001..009)."""
    bal, created = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        year=year,
        category=category,
        defaults={"allocated": ent.yearly_credit(category), "used": 0.0, "pending": 0.0},
    )
    return bal


def initialize_user_balances(user_id: int, year: int) -> list[LeaveBalance]:
    """Pre-seed annual balances for all standard categories."""
    balances = []
    for cat in ("CL", "RH", "SCL", "EL", "COL", "VL"):
        balances.append(get_or_create_balance(user_id, year, cat))
    return balances


def submit_leave(
    *,
    user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    purpose: str = "",
    half_day: bool = False,
    half_day_period: str = "none",
    station_leave: bool = False,
    station_details: str = "",
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Validate, calculate debit, verify balance, verify non-overlap, and create request."""
    if start_date > end_date:
        raise BadRequestError("start_date cannot be after end_date.", code="invalid_dates")

    if station_leave and not station_details.strip():
        raise BadRequestError(
            "Station details are mandatory when requesting station leave (BR-EL-013).",
            code="missing_station_details",
        )

    if half_day and category != "CL":
        raise BadRequestError("Half-day leave is only permitted for Casual Leave (CL) (BR-EL-010).")

    if half_day and half_day_period not in ("FN", "AN"):
        raise BadRequestError("Half-day leave requires specifying period as Forenoon (FN) or Afternoon (AN).")

    days_count = ent.calculate_days(category, start_date, end_date, half_day=half_day)
    year = start_date.year

    with transaction.atomic():
        # 1. Enforce applicant non-overlap with half-day CL exception (BR-EL-012)
        existing = LeaveRequest.objects.filter(user_id=user_id)
        try:
            ent.validate_non_overlap(
                existing, start_date, end_date, new_half_day=half_day, new_period=half_day_period
            )
        except ent.OverlapError as exc:
            raise ConflictError(str(exc), code="leave_overlap") from exc

        # 2. Verify and debit pending balance
        bal = get_or_create_balance(user_id, year, category)
        if bal.available < days_count:
            raise ConflictError(
                f"Insufficient leave balance for {category}: requested {days_count} days, "
                f"available {bal.available} days.",
                code="insufficient_balance",
            )

        bal.pending += days_count
        bal.save(update_fields=["pending", "updated_at"])

        # 3. Create leave request
        sub_status = "pending" if substitute_user_id else "none"
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            half_day_period=half_day_period if half_day else "none",
            days_count=days_count,
            purpose=purpose,
            station_leave=station_leave,
            station_details=station_details,
            substitute_user_id=substitute_user_id,
            substitute_status=sub_status,
            status=sm.DRAFT,
        )

        initial_target = sm.AWAITING_SUB if substitute_user_id else sm.UNIT_HEAD
        move(req, to_status=initial_target, actor=None, reason="Initial submission")
        return req


def move(req: LeaveRequest, *, to_status: str, actor, reason: str = "") -> LeaveRequest:
    """Internal state transition dispatcher with balance ledger adjustments."""
    kind = actor_kind(actor, req)
    resolve_or_raise(req.status, to_status, kind)
    frm = req.status
    req.status = to_status

    year = req.start_date.year
    bal = get_or_create_balance(req.user_id, year, req.category)

    # Balance ledger synchronization
    if to_status == sm.APPROVED:
        bal.pending = max(0.0, bal.pending - req.days_count)
        bal.used += req.days_count
        bal.save(update_fields=["pending", "used", "updated_at"])
    elif to_status in (sm.REJECTED, sm.WITHDRAWN):
        if frm != sm.APPROVED:  # Pending was reserved
            bal.pending = max(0.0, bal.pending - req.days_count)
            bal.save(update_fields=["pending", "updated_at"])
    elif to_status == sm.CANCELLED:
        if frm == sm.APPROVED:
            bal.used = max(0.0, bal.used - req.days_count)
            bal.save(update_fields=["used", "updated_at"])
        elif frm != sm.DRAFT:
            bal.pending = max(0.0, bal.pending - req.days_count)
            bal.save(update_fields=["pending", "updated_at"])

    req.save(update_fields=["status", "rejection_reason", "updated_at"])
    LeaveTransition.objects.create(
        request=req,
        from_status=frm,
        to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        reason=reason,
    )
    return req


def respond_as_substitute(
    *, request_id: int, substitute_user_id: int, accept: bool, remarks: str = ""
) -> LeaveRequest:
    """Substitute consent gate handling (BR-EL-015)."""
    with transaction.atomic():
        try:
            req = LeaveRequest.objects.select_for_update().get(pk=request_id)
        except LeaveRequest.DoesNotExist as exc:
            raise NotFoundError("Leave request not found.") from exc

        if req.substitute_user_id != substitute_user_id:
            raise PermissionDeniedError("You are not the designated substitute for this request.")

        if req.status != sm.AWAITING_SUB:
            raise ConflictError(f"Request is in '{req.status}' state, not awaiting substitute consent.")

        req.substitute_remarks = remarks
        if accept:
            req.substitute_status = "accepted"
            req.save(update_fields=["substitute_status", "substitute_remarks", "updated_at"])
            class SubActor:
                user_id = substitute_user_id
            return move(req, to_status=sm.UNIT_HEAD, actor=SubActor(), reason=f"Substitute accepted: {remarks}".strip())
        else:
            req.substitute_status = "declined"
            req.rejection_reason = f"Substitute declined: {remarks}".strip()
            req.save(update_fields=["substitute_status", "substitute_remarks", "rejection_reason", "updated_at"])
            class SubActor:
                user_id = substitute_user_id
            return move(req, to_status=sm.REJECTED, actor=SubActor(), reason=req.rejection_reason)


def transition(
    *, request_id: int, to_status: str, actor, reason: str = "", scope=None
) -> LeaveRequest:
    """Public transition API: Unit head recommend/sanction, Authority decision, Cancellation."""
    qs = scope if scope is not None else LeaveRequest.objects.all()
    try:
        req = qs.get(pk=request_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.") from exc

    if to_status == sm.REJECTED and not reason.strip():
        raise BadRequestError("A clear rejection reason is mandatory when rejecting leave (BR-EL-016..019).")

    if to_status == sm.CANCELLED and req.start_date < datetime.date.today():
        raise BadRequestError("Cannot cancel leave after its commencement date (BR-EL-023).")

    with transaction.atomic():
        locked = LeaveRequest.objects.select_for_update().get(pk=req.pk)
        if to_status == sm.REJECTED:
            locked.rejection_reason = reason
        return move(locked, to_status=to_status, actor=actor, reason=reason)
