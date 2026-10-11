"""Write paths: apply, respond, decide, withdraw, cancel.

Validation lives here, in terms of the pure rules in `domain/`. Every rule is
raised as a domain error (never a DRF one), so these services stay callable
from a task or a command.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm import selectors
from modules.elm.domain import categories
from modules.elm.domain.categories import LeaveCategory
from modules.elm.domain.state_machine import LeaveStatus, SubstituteStatus, transition_for
from modules.elm.models import HolidayCalendar, LeaveApplication, LeaveBalance, LeaveTransaction

log = logging.getLogger("fusion.elm")


def _published_holidays() -> frozenset:
    return frozenset(HolidayCalendar.objects.filter(is_published=True)
                     .values_list("date", flat=True))


def ensure_balances(user_id: int, year: int, kind: str) -> None:
    """Create the entitlement rows for one employee, once, for a year."""
    for cat in LeaveCategory:
        ent = categories.entitlement(cat, kind=kind)
        _balance, created = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, category=cat.value,
            defaults={"entitled": ent})
        if created and ent > 0:
            LeaveTransaction.objects.create(
                user_id=user_id, year=year, category=cat.value, amount=ent,
                reason=LeaveTransaction.OPENING)


def _active_overlaps(user_id: int, start, end, half: str) -> bool:
    qs = (LeaveApplication.objects
          .filter(user_id=user_id, status__in=selectors.ACTIVE_STATUSES))
    for other in qs:
        if categories.overlaps(start, end, half,
                               other.start_date, other.end_date, other.half):
            return True
    return False


def apply(*, user_id: int, kind: str, category: str, start_date, end_date,
          half: str, purpose: str, station_leave=None,
          substitute_user_id=None) -> LeaveApplication:
    cat = LeaveCategory(category)
    if end_date < start_date:
        from core.api.exceptions import BadRequestError
        raise BadRequestError("end_date precedes start_date.",
                              code="dates_reversed")

    year = start_date.year
    with transaction.atomic():
        ensure_balances(user_id, year, kind)

        if cat is LeaveCategory.VL and kind != "faculty":
            raise ConflictError("Vacation leave is available to faculty only.",
                                code="vl_faculty_only")

        days = categories.count_days(cat, start_date, end_date, half=half,
                                     holidays=_published_holidays())
        if days <= 0:
            from core.api.exceptions import BadRequestError
            raise BadRequestError("The requested period contains no leave days.",
                                  code="no_leave_days")

        if _active_overlaps(user_id, start_date, end_date, half):
            raise ConflictError(
                "The requested period overlaps existing pending or approved leave.",
                code="leave_overlap")

        balance = (LeaveBalance.objects.select_for_update()
                   .get(user_id=user_id, year=year, category=cat.value))
        if balance.available < days:
            raise ConflictError(
                f"Insufficient {cat.label} balance: {balance.available} day(s) "
                f"available, {days} requested.",
                code="insufficient_balance")

        substitute_status = SubstituteStatus.NONE.value
        if substitute_user_id is not None:
            if substitute_user_id == user_id:
                raise ConflictError("You cannot nominate yourself as substitute.",
                                    code="self_substitute")
            if _active_overlaps(substitute_user_id, start_date, end_date, half):
                raise ConflictError(
                    "The nominated substitute has overlapping pending or approved leave.",
                    code="substitute_overlap")
            substitute_status = SubstituteStatus.PENDING.value

        return LeaveApplication.objects.create(
            user_id=user_id, category=cat.value, start_date=start_date,
            end_date=end_date, half=half, purpose=purpose,
            station_leave=station_leave, substitute_user_id=substitute_user_id,
            substitute_status=substitute_status,
            status=LeaveStatus.SUBMITTED.value, chargeable_days=days)


def respond_substitute(*, user_id: int, application_id: int,
                       accept: bool) -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.substitute_user_id != user_id:
            raise NotFoundError("No substitute nomination for you on that request.")
        if app.status != LeaveStatus.SUBMITTED.value:
            raise ConflictError("That request is no longer pending.",
                                code="not_pending")
        if app.substitute_status != SubstituteStatus.PENDING.value:
            raise ConflictError("The substitute has already responded.",
                                code="already_responded")
        app.substitute_status = (SubstituteStatus.ACCEPTED.value if accept
                                 else SubstituteStatus.DECLINED.value)
        app.save(update_fields=["substitute_status", "updated_at"])
    return app


def decide(*, actor_user_id: int, application_id: int, approve: bool,
           note: str = "") -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.status != LeaveStatus.SUBMITTED.value:
            raise ConflictError("That request has already been decided.",
                                code="not_pending")
        if app.substitute_status == SubstituteStatus.PENDING.value:
            raise ConflictError("Substitute consent is still awaited.",
                                code="consent_pending")
        if app.substitute_status == SubstituteStatus.DECLINED.value:
            raise ConflictError(
                "The substitute declined; the applicant must re-nominate or withdraw.",
                code="substitute_declined")

        to = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        transition_for(LeaveStatus.SUBMITTED, to)

        if approve:
            balance = (LeaveBalance.objects.select_for_update()
                       .get(user_id=app.user_id, year=app.start_date.year,
                            category=app.category))
            balance.used = balance.used + app.chargeable_days
            balance.save(update_fields=["used"])
            LeaveTransaction.objects.create(
                user_id=app.user_id, year=app.start_date.year,
                category=app.category, amount=-app.chargeable_days,
                reason=LeaveTransaction.APPROVED, application_id=app.id)

        app.status = to.value
        app.decided_by_user_id = actor_user_id
        app.decided_at = timezone.now()
        app.decision_note = note
        app.save(update_fields=["status", "decided_by_user_id", "decided_at",
                                "decision_note", "updated_at"])
    return app


def withdraw(*, user_id: int, application_id: int) -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status != LeaveStatus.SUBMITTED.value:
            raise ConflictError("Only a pending request can be withdrawn.",
                                code="not_pending")
        transition_for(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN)
        app.status = LeaveStatus.WITHDRAWN.value
        app.save(update_fields=["status", "updated_at"])
    return app


def cancel(*, user_id: int, application_id: int) -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status != LeaveStatus.APPROVED.value:
            raise ConflictError("Only an approved leave can be cancelled.",
                                code="not_approved")
        if app.start_date <= timezone.localdate():
            raise ConflictError(
                "The leave has begun; cancellation is no longer available.",
                code="already_started")
        transition_for(LeaveStatus.APPROVED, LeaveStatus.CANCELLED)

        balance = (LeaveBalance.objects.select_for_update()
                   .get(user_id=app.user_id, year=app.start_date.year,
                        category=app.category))
        balance.used = max(Decimal("0"), balance.used - app.chargeable_days)
        balance.save(update_fields=["used"])
        LeaveTransaction.objects.create(
            user_id=app.user_id, year=app.start_date.year, category=app.category,
            amount=app.chargeable_days, reason=LeaveTransaction.CANCELLED,
            application_id=app.id)

        app.status = LeaveStatus.CANCELLED.value
        app.save(update_fields=["status", "updated_at"])
    return app
