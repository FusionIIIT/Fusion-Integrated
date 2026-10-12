"""Return-to-duty resumption for continuous leave (EL-UC-010, BR-EL-027/028)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.domain import enums as e
from modules.elm.models import LeaveRequest, ResumptionRecord
from modules.elm.services import accounts, notifications


def _fail(code: str, message: str):
    raise ConflictError(message, code=code)


def _classify(*, scheduled: date, actual: date) -> tuple[str, Decimal]:
    if actual == scheduled:
        return e.RES_NORMAL, Decimal("0")
    if actual < scheduled:
        return e.RES_EARLY, Decimal((scheduled - actual).days)
    return e.RES_LATE, Decimal((actual - scheduled).days)


@transaction.atomic
def submit(*, actor, request_id: int, actual_date: date,
           details: str = "") -> ResumptionRecord:
    request = LeaveRequest.objects.filter(pk=request_id).first()
    if request is None or request.user_id != actor.user_id:
        _fail("not_found", "No such leave request.")
    if request.status != e.APPROVED or request.kind != e.NEW:
        _fail("not_approved", "Only an approved leave can be resumed.")
    if request.category not in e.RESUMPTION:
        _fail("no_resumption", f"{request.category} leave has no resumption step.")
    if request.start_date > actual_date:
        _fail("bad_date", "The resumption date cannot precede the leave start.")
    if ResumptionRecord.objects.filter(request=request).exists():
        _fail("duplicate", "A resumption has already been recorded for this leave.")

    outcome, delta = _classify(scheduled=request.end_date, actual=actual_date)
    record = ResumptionRecord.objects.create(
        request=request, user_id=request.user_id, actual_date=actual_date,
        details=details, status="pending", outcome=outcome,
        adjustment_note=(f"{outcome}: {delta} day(s)"))

    account = accounts.ensure_account(request.user_id, request.category,
                                      request.start_date.year)
    if outcome == e.RES_EARLY and delta > 0:
        accounts.restore(account=account, days=delta, request=request,
                         actor_user_id=actor.user_id,
                         note=f"Early resumption ({actual_date.isoformat()})")
    elif outcome == e.RES_LATE and delta > 0:
        accounts.deduct(account=account, days=delta, request=request,
                        actor_user_id=actor.user_id,
                        note=f"Late resumption ({actual_date.isoformat()})")

    notifications.enqueue(
        topic="request.resumption_reviewed",
        dedupe_key=f"resumption:req{request.pk}",
        subject=f"Resumption recorded for leave #{request.pk}",
        body=f"Your return on {actual_date.isoformat()} was recorded ({outcome}).",
        recipient_user_id=request.user_id, payload={"request_id": request.pk})
    return record


@transaction.atomic
def review(*, actor, record_id: int, note: str = "") -> ResumptionRecord:
    record = ResumptionRecord.objects.filter(pk=record_id).first()
    if record is None:
        _fail("not_found", "No such resumption record.")
    if record.status == "reviewed":
        _fail("already_reviewed", "This resumption has already been reviewed.")
    record.status = "reviewed"
    record.reviewed_by_user_id = actor.user_id
    record.reviewed_at = timezone.now()
    if note:
        record.adjustment_note = note
    record.save(update_fields=["status", "reviewed_by_user_id", "reviewed_at",
                               "adjustment_note", "updated_at"])
    return record


def overdue():
    """Approved continuous leave whose end date has passed with no resumption."""
    today = timezone.localdate()
    return (LeaveRequest.objects
            .filter(kind=e.NEW, status=e.APPROVED,
                    category__in=e.RESUMPTION, end_date__lt=today)
            .exclude(pk__in=ResumptionRecord.objects.values("request_id")))
