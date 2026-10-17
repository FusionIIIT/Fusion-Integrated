"""Writes. Every change to a request or a balance goes through here, inside a
transaction, with the rows it depends on locked."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.domain.entities import (
    Balance,
    HalfDay,
    LeaveCategory,
    LeaveSpan,
    LeaveStatus,
)
from modules.elm.domain.errors import InvalidTransition, LeaveRuleViolation
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveRequestTransition
from modules.elm.selectors import leaves as selectors

_PENDING = [LeaveStatus.PENDING, LeaveStatus.RECOMMENDED, LeaveStatus.NOT_RECOMMENDED]


def _rule_error(exc: LeaveRuleViolation) -> DomainError:
    return DomainError(exc.message, code=exc.code)


def _balance_row(user_id: int, year: int, category: LeaveCategory, kind: str,
                 *, lock: bool = False) -> LeaveBalance:
    row, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=category,
        defaults={"credited": policy.entitlement_for(category, kind)})
    if lock:
        row = LeaveBalance.objects.select_for_update().get(pk=row.pk)
    return row


def _reserved(user_id: int, year: int, category: LeaveCategory) -> Decimal:
    """Days held by requests that are still in flight, so two pending requests
    cannot both spend the same balance."""
    total = (LeaveRequest.objects
             .filter(applicant_user_id=user_id, category=category,
                     start_date__year=year, status__in=_PENDING)
             .aggregate(t=Sum("days"))["t"])
    return total or Decimal(0)


def balances(principal, year: int) -> list[Balance]:
    out = []
    for category in LeaveCategory:
        if policy.entitlement_for(category, principal.kind) == 0 and not \
                LeaveBalance.objects.filter(user_id=principal.user_id, year=year,
                                            category=category).exists():
            continue                 # e.g. VL for staff: nothing to show
        row = _balance_row(principal.user_id, year, category, principal.kind)
        out.append(Balance(category, row.credited, row.availed,
                           _reserved(principal.user_id, year, category)))
    return out


def submit(principal, *, category: str, start_date: date, end_date: date,
           half: str = "", reason: str, is_station_leave: bool = False,
           station_address: str = "", station_contact: str = "") -> LeaveRequest:
    category = LeaveCategory(category)
    span = LeaveSpan(start_date, end_date, HalfDay(half))
    with transaction.atomic():
        # Locking the balance row serialises this employee's submissions for
        # the category, so the balance and overlap checks cannot race.
        row = _balance_row(principal.user_id, start_date.year, category,
                           principal.kind, lock=True)
        balance = Balance(category, row.credited, row.availed,
                          _reserved(principal.user_id, start_date.year, category))
        try:
            days = policy.validate_new_request(
                category=category, kind=principal.kind, span=span, balance=balance,
                existing=selectors.active_spans(principal.user_id),
                is_station_leave=is_station_leave, station_address=station_address,
                station_contact=station_contact)
        except LeaveRuleViolation as exc:
            raise _rule_error(exc) from exc

        req = LeaveRequest.objects.create(
            applicant_user_id=principal.user_id, category=category,
            start_date=start_date, end_date=end_date, half=span.half, days=days,
            reason=reason, is_station_leave=is_station_leave,
            station_address=station_address if is_station_leave else "",
            station_contact=station_contact if is_station_leave else "")
        LeaveRequestTransition.objects.create(
            request=req, from_status="", to_status=LeaveStatus.PENDING,
            actor_user_id=principal.user_id, remarks="Submitted")
    return req


def allowed_targets(req: LeaveRequest, principal) -> list[str]:
    return sm.allowed_targets(req.status, req.category,
                              permissions=principal.permissions,
                              is_applicant=req.applicant_user_id == principal.user_id)


def transition(*, request_id: int, to_status: str, principal,
               remarks: str = "") -> LeaveRequest:
    with transaction.atomic():
        try:
            req = (selectors.visible_requests(principal)
                   .select_for_update().get(pk=request_id))
        except LeaveRequest.DoesNotExist as exc:
            raise NotFoundError("Leave request not found.") from exc
        frm = req.status
        try:
            sm.resolve(frm, to_status, req.category, permissions=principal.permissions,
                       is_applicant=req.applicant_user_id == principal.user_id)
        except InvalidTransition as exc:
            cls = PermissionDeniedError if exc.denied else ConflictError
            raise cls(f"Cannot move this request from '{frm}' to '{to_status}': "
                      f"{exc.reason}.", code="invalid_transition",
                      details=[{"from": frm, "to": to_status,
                                "allowed": allowed_targets(req, principal)}]) from exc

        if to_status == LeaveStatus.APPROVED:
            # Balance is only spent on final approval; until then it is reserved.
            row = LeaveBalance.objects.select_for_update().get(
                user_id=req.applicant_user_id, year=req.start_date.year,
                category=req.category)
            row.availed += req.days
            row.save(update_fields=["availed", "updated_at"])

        req.status = to_status
        req.save(update_fields=["status", "updated_at"])
        LeaveRequestTransition.objects.create(
            request=req, from_status=frm, to_status=to_status,
            actor_user_id=principal.user_id, remarks=remarks[:500])
    return req
