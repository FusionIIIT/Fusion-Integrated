"""Write paths: apply, respond, recommend, decide, withdraw, cancel, resume, offline.

Validation lives here, in terms of the pure rules in `domain/`. Every rule is
raised as a domain error (never a DRF one), so these services stay callable
from a task or a command.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm import selectors
from modules.elm.domain import categories
from modules.elm.domain.categories import LeaveCategory
from modules.elm.domain.state_machine import LeaveStatus, SubstituteStatus, transition_for
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveTransaction,
    VacationCalendar,
)

log = logging.getLogger("fusion.elm")


def _published_holidays() -> frozenset:
    return frozenset(HolidayCalendar.objects.filter(
        is_published=True,
        kind=HolidayCalendar.HOLIDAY,
    ).values_list("date", flat=True))


def _is_published_rh(date_val) -> bool:
    return HolidayCalendar.objects.filter(
        is_published=True,
        kind=HolidayCalendar.RESTRICTED,
        date=date_val,
    ).exists()


def _is_within_vacation(start_date, end_date) -> bool:
    """BR-EL-006: Faculty VL may only be availed during vacation periods."""
    return VacationCalendar.objects.filter(
        is_active=True,
        start_date__lte=start_date,
        end_date__gte=end_date,
    ).exists()


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
          half: str = "full", purpose: str = "", department: str = "",
          station_leave=None, substitute_user_id=None,
          is_director: bool = False) -> LeaveApplication:
    cat = LeaveCategory(category)
    if end_date < start_date:
        raise BadRequestError("end_date precedes start_date.",
                              code="dates_reversed")

    if half != "full":
        if not categories.supports_half_day(cat):
            raise BadRequestError(f"{cat.label} does not support half-day requests.",
                                  code="half_day_unsupported")
        if start_date != end_date:
            raise BadRequestError("Half-day leave must be for a single date.",
                                  code="half_day_multi_date")

    year = start_date.year
    with transaction.atomic():
        ensure_balances(user_id, year, kind)

        if cat is LeaveCategory.VL:
            if kind != "faculty":
                raise ConflictError("Vacation leave is available to faculty only.",
                                    code="vl_faculty_only")
            if not _is_within_vacation(start_date, end_date):
                raise ConflictError(
                    "Vacation Leave may be availed only during an applicable academic vacation "
                    "period.",
                    code="vl_outside_vacation")

        if cat is LeaveCategory.RH:
            if start_date != end_date:
                raise BadRequestError("Restricted holiday leave must be taken on a single day.",
                                      code="rh_single_day")
            if not _is_published_rh(start_date):
                raise ConflictError("The selected date is not a published Restricted Holiday.",
                                    code="rh_not_published")

        days = categories.count_days(cat, start_date, end_date, half=half,
                                     holidays=_published_holidays())
        if days <= 0:
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

        # Director self-sanction (BR-EL-020)
        if is_director:
            balance.used = balance.used + days
            balance.save(update_fields=["used"])
            app = LeaveApplication.objects.create(
                user_id=user_id, department=department, category=cat.value,
                start_date=start_date, end_date=end_date, half=half,
                purpose=purpose, station_leave=station_leave,
                substitute_user_id=substitute_user_id,
                substitute_status=substitute_status,
                status=LeaveStatus.APPROVED.value, chargeable_days=days,
                decided_by_user_id=user_id, decided_at=timezone.now(),
                decision_note="Director self-sanction")
            LeaveTransaction.objects.create(
                user_id=user_id, year=year, category=cat.value, amount=-days,
                reason=LeaveTransaction.APPROVED, application_id=app.id)
            return app

        return LeaveApplication.objects.create(
            user_id=user_id, department=department, category=cat.value,
            start_date=start_date, end_date=end_date, half=half,
            purpose=purpose, station_leave=station_leave,
            substitute_user_id=substitute_user_id,
            substitute_status=substitute_status,
            status=LeaveStatus.SUBMITTED.value, chargeable_days=days)


def respond_substitute(*, user_id: int, application_id: int,
                       accept: bool) -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.substitute_user_id != user_id:
            raise NotFoundError("No substitute nomination for you on that request.")
        if app.status not in (LeaveStatus.SUBMITTED.value, LeaveStatus.FORWARDED.value):
            raise ConflictError("That request is no longer pending.",
                                code="not_pending")
        if app.substitute_status != SubstituteStatus.PENDING.value:
            raise ConflictError("The substitute has already responded.",
                                code="already_responded")
        app.substitute_status = (SubstituteStatus.ACCEPTED.value if accept
                                 else SubstituteStatus.DECLINED.value)
        app.save(update_fields=["substitute_status", "updated_at"])
    return app


def renominate_substitute(*, user_id: int, application_id: int,
                          substitute_user_id: int) -> LeaveApplication:
    """Applicant nominates replacement substitute after decline (EL-UC-019, BR-EL-015)."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status != LeaveStatus.SUBMITTED.value:
            raise ConflictError("Replacement substitute may be nominated only on pending requests.",
                                code="not_pending")
        if app.substitute_status != SubstituteStatus.DECLINED.value:
            raise ConflictError("Replacement substitute may be nominated only after a decline.",
                                code="not_declined")
        if substitute_user_id == user_id:
            raise ConflictError("You cannot nominate yourself as substitute.",
                                code="self_substitute")
        if _active_overlaps(substitute_user_id, app.start_date, app.end_date, app.half):
            raise ConflictError(
                "The nominated substitute has overlapping pending or approved leave.",
                code="substitute_overlap")

        app.substitute_user_id = substitute_user_id
        app.substitute_status = SubstituteStatus.PENDING.value
        app.save(update_fields=["substitute_user_id", "substitute_status", "updated_at"])
    return app


def recommend(*, actor_user_id: int, application_id: int,
              recommended: bool, note: str = "") -> LeaveApplication:
    """Unit Head records recommendation for higher-sanction categories (BR-EL-017)."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        if app.user_id == actor_user_id:
            raise ConflictError("You cannot review your own leave request.",
                                code="self_review")
        if app.status != LeaveStatus.SUBMITTED.value:
            raise ConflictError("That request is not awaiting recommendation.",
                                code="not_submitted")
        cat = LeaveCategory(app.category)
        if not categories.requires_higher_sanction(cat):
            raise ConflictError(
                f"{cat.label} does not require higher sanction; decide it directly.",
                code="no_recommendation_needed")
        if app.substitute_status == SubstituteStatus.PENDING.value:
            raise ConflictError("Substitute consent is still awaited.",
                                code="consent_pending")
        if app.substitute_status == SubstituteStatus.DECLINED.value:
            raise ConflictError(
                "The substitute declined; applicant must re-nominate or withdraw.",
                code="substitute_declined")

        transition_for(LeaveStatus.SUBMITTED, LeaveStatus.FORWARDED)
        app.status = LeaveStatus.FORWARDED.value
        app.recommended_by_user_id = actor_user_id
        app.recommended_at = timezone.now()
        app.recommendation = "recommended" if recommended else "not_recommended"
        app.recommendation_note = note
        app.save(update_fields=["status", "recommended_by_user_id",
                                "recommended_at", "recommendation",
                                "recommendation_note", "updated_at"])
    return app


def decide(*, actor_user_id: int, application_id: int, approve: bool,
           note: str = "") -> LeaveApplication:
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.user_id == actor_user_id:
            raise ConflictError("You cannot decide your own leave request.",
                                code="self_decision")
        if app.status not in (LeaveStatus.SUBMITTED.value, LeaveStatus.FORWARDED.value):
            raise ConflictError("That request is not awaiting a decision.",
                                code="not_pending")

        cat = LeaveCategory(app.category)
        if app.status == LeaveStatus.SUBMITTED.value and categories.requires_higher_sanction(cat):
            raise ConflictError(
                f"{cat.label} requires Unit Head recommendation before final sanction.",
                code="recommendation_required")

        if app.substitute_status == SubstituteStatus.PENDING.value:
            raise ConflictError("Substitute consent is still awaited.",
                                code="consent_pending")
        if app.substitute_status == SubstituteStatus.DECLINED.value:
            raise ConflictError(
                "The substitute declined; the applicant must re-nominate or withdraw.",
                code="substitute_declined")

        current_status = LeaveStatus(app.status)
        to = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        transition_for(current_status, to)

        if approve:
            balance = (LeaveBalance.objects.select_for_update()
                       .get(user_id=app.user_id, year=app.start_date.year,
                            category=app.category))
            if balance.available < app.chargeable_days:
                raise ConflictError(
                    f"Insufficient balance at decision time: {balance.available} available, "
                    f"{app.chargeable_days} required.",
                    code="insufficient_balance")
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
    """Immediate withdrawal of pending request before final decision (BR-EL-022)."""
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status not in (LeaveStatus.SUBMITTED.value, LeaveStatus.FORWARDED.value):
            raise ConflictError("Only a pending request can be withdrawn.",
                                code="not_pending")
        transition_for(LeaveStatus(app.status), LeaveStatus.WITHDRAWN)
        app.status = LeaveStatus.WITHDRAWN.value
        app.save(update_fields=["status", "updated_at"])
    return app


def request_cancellation(*, user_id: int, application_id: int) -> LeaveApplication:
    """Applicant requests cancellation of approved leave before it begins (BR-EL-023)."""
    with transaction.atomic():
        app = (LeaveApplication.objects.select_for_update()
               .get(pk=application_id))
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status != LeaveStatus.APPROVED.value:
            raise ConflictError("Only an approved leave can be requested for cancellation.",
                                code="not_approved")
        if app.start_date <= timezone.localdate():
            raise ConflictError(
                "The leave has already begun; cancellation is no longer available.",
                code="already_started")
        transition_for(LeaveStatus.APPROVED, LeaveStatus.CANCELLATION_REQUESTED)
        app.status = LeaveStatus.CANCELLATION_REQUESTED.value
        app.save(update_fields=["status", "updated_at"])
    return app


def decide_cancellation(*, actor_user_id: int, application_id: int,
                        approve: bool, note: str = "") -> LeaveApplication:
    """Sanctioning authority approves or rejects cancellation (BR-EL-023)."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        if app.user_id == actor_user_id:
            raise ConflictError("You cannot decide cancellation on your own leave.",
                                code="self_decision")
        if app.status != LeaveStatus.CANCELLATION_REQUESTED.value:
            raise ConflictError("That request is not awaiting cancellation review.",
                                code="not_cancellation_requested")

        to = LeaveStatus.CANCELLED if approve else LeaveStatus.APPROVED
        transition_for(LeaveStatus.CANCELLATION_REQUESTED, to)

        if approve:
            balance = (LeaveBalance.objects.select_for_update()
                       .get(user_id=app.user_id, year=app.start_date.year,
                            category=app.category))
            balance.used = max(Decimal("0"), balance.used - app.chargeable_days)
            balance.save(update_fields=["used"])
            LeaveTransaction.objects.create(
                user_id=app.user_id, year=app.start_date.year, category=app.category,
                amount=app.chargeable_days, reason=LeaveTransaction.CANCELLED,
                application_id=app.id)

        app.status = to.value
        app.decided_by_user_id = actor_user_id
        app.decided_at = timezone.now()
        app.decision_note = note
        app.save(update_fields=["status", "decided_by_user_id", "decided_at",
                                "decision_note", "updated_at"])
    return app


def submit_resumption(*, user_id: int, application_id: int,
                      actual_resumption_date, note: str = "") -> LeaveApplication:
    """Employee reports return to duty for EL, COL, VL (BR-EL-027)."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        if app.user_id != user_id:
            raise NotFoundError("No such leave request.")
        if app.status != LeaveStatus.APPROVED.value:
            raise ConflictError("Resumption may be submitted only for approved leave.",
                                code="not_approved")
        cat = LeaveCategory(app.category)
        if cat not in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
            raise ConflictError(
                "Formal resumption review applies only to EL, COL, and VL.",
                code="resumption_not_applicable")

        transition_for(LeaveStatus.APPROVED, LeaveStatus.RESUMPTION_REQUESTED)
        app.status = LeaveStatus.RESUMPTION_REQUESTED.value
        app.actual_resumption_date = actual_resumption_date
        app.resumption_note = note
        app.save(update_fields=["status", "actual_resumption_date",
                                "resumption_note", "updated_at"])
    return app


def review_resumption(*, actor_user_id: int, application_id: int,
                      note: str = "") -> LeaveApplication:
    """Authority reviews duty resumption and synchronizes attendance/balance (BR-EL-028)."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        if app.user_id == actor_user_id:
            raise ConflictError("You cannot review resumption of your own leave.",
                                code="self_review")
        if app.status != LeaveStatus.RESUMPTION_REQUESTED.value:
            raise ConflictError("That request is not awaiting resumption review.",
                                code="not_resumption_requested")

        transition_for(LeaveStatus.RESUMPTION_REQUESTED, LeaveStatus.RESUMED)
        actual = app.actual_resumption_date
        cat = LeaveCategory(app.category)
        balance = (LeaveBalance.objects.select_for_update()
                   .get(user_id=app.user_id, year=app.start_date.year,
                        category=app.category))

        # Compare actual leave days vs originally charged days
        if actual <= app.end_date:
            # Early resumption: returned before or on the approved end date
            new_end = actual - timedelta(days=1)
            actual_days = (Decimal("0") if new_end < app.start_date
                           else categories.count_days(cat, app.start_date, new_end,
                                                     half=app.half,
                                                     holidays=_published_holidays()))
            adjustment = app.chargeable_days - actual_days
            if adjustment > 0:
                balance.used = max(Decimal("0"), balance.used - adjustment)
                balance.save(update_fields=["used"])
                LeaveTransaction.objects.create(
                    user_id=app.user_id, year=app.start_date.year, category=app.category,
                    amount=adjustment, reason=LeaveTransaction.RESUMPTION,
                    application_id=app.id)
                app.chargeable_days = actual_days
        elif actual > app.end_date + timedelta(days=1):
            # Late resumption: employee was absent beyond approved end date
            actual_end = actual - timedelta(days=1)
            actual_days = categories.count_days(cat, app.start_date, actual_end,
                                               half=app.half,
                                               holidays=_published_holidays())
            additional = actual_days - app.chargeable_days
            if additional > 0:
                balance.used = balance.used + additional
                balance.save(update_fields=["used"])
                LeaveTransaction.objects.create(
                    user_id=app.user_id, year=app.start_date.year, category=app.category,
                    amount=-additional, reason=LeaveTransaction.RESUMPTION,
                    application_id=app.id)
                app.chargeable_days = actual_days

        app.status = LeaveStatus.RESUMED.value
        app.decided_by_user_id = actor_user_id
        app.decided_at = timezone.now()
        app.decision_note = note
        app.save(update_fields=["status", "chargeable_days", "decided_by_user_id",
                                "decided_at", "decision_note", "updated_at"])
    return app


def record_offline_leave(*, admin_user_id: int, user_id: int, kind: str,
                         category: str, start_date, end_date, half: str = "full",
                         purpose: str = "", sanction_reference: str = "",
                         department: str = "") -> LeaveApplication:
    """Leave Administrator records already-sanctioned offline leave
    (BR-EL-029, BR-EL-037, EL-UC-016)."""
    if not sanction_reference or not sanction_reference.strip():
        raise BadRequestError("Sanction reference evidence is required for offline leave.",
                              code="missing_reference")
    cat = LeaveCategory(category)
    if end_date < start_date:
        raise BadRequestError("end_date precedes start_date.",
                              code="dates_reversed")

    year = start_date.year
    with transaction.atomic():
        ensure_balances(user_id, year, kind)
        days = categories.count_days(cat, start_date, end_date, half=half,
                                     holidays=_published_holidays())
        balance = (LeaveBalance.objects.select_for_update()
                   .get(user_id=user_id, year=year, category=cat.value))
        if balance.available < days:
            raise ConflictError(
                f"Insufficient balance: {balance.available} available, {days} required.",
                code="insufficient_balance")

        balance.used = balance.used + days
        balance.save(update_fields=["used"])

        app = LeaveApplication.objects.create(
            user_id=user_id, department=department, category=cat.value,
            start_date=start_date, end_date=end_date, half=half, purpose=purpose,
            status=LeaveStatus.APPROVED.value, chargeable_days=days,
            decided_by_user_id=admin_user_id, decided_at=timezone.now(),
            decision_note=f"Offline sanctioned: {sanction_reference}",
            is_offline_record=True, offline_sanction_reference=sanction_reference)

        LeaveTransaction.objects.create(
            user_id=user_id, year=year, category=cat.value, amount=-days,
            reason=LeaveTransaction.OFFLINE, application_id=app.id)
    return app


def process_year_end(*, year: int) -> dict[str, int]:
    """Execute event-triggered year-end leave processing (BR-EL-007, BR-EL-008, EL-UC-020)."""
    processed_count = 0
    next_year = year + 1
    with transaction.atomic():
        user_ids = set(LeaveBalance.objects.filter(year=year)
                       .values_list("user_id", flat=True))
        for uid in user_ids:
            balances = {b.category: b for b in LeaveBalance.objects.filter(user_id=uid, year=year)}

            # 1. Faculty VL -> convert unused VL to EL at 2:1 and credit to next year EL
            vl = balances.get(LeaveCategory.VL.value)
            converted_el = Decimal("0")
            if vl and vl.available > 0:
                converted_el = categories.convert_vl_to_el(vl.available)
                LeaveTransaction.objects.create(
                    user_id=uid, year=year, category=LeaveCategory.VL.value,
                    amount=-vl.available, reason=LeaveTransaction.CONVERSION)

            # 2. EL carry-forward (non-faculty entitlement + any converted EL)
            el = balances.get(LeaveCategory.EL.value)
            el_cf = el.available if (el and el.available > 0) else Decimal("0")

            # 3. COL carry-forward
            col = balances.get(LeaveCategory.COL.value)
            col_cf = col.available if (col and col.available > 0) else Decimal("0")

            # Create or update next year's balances
            if el_cf > 0 or converted_el > 0:
                next_el, _ = LeaveBalance.objects.get_or_create(
                    user_id=uid, year=next_year, category=LeaveCategory.EL.value,
                    defaults={"entitled": Decimal("0")})
                total_credit = el_cf + converted_el
                next_el.entitled += total_credit
                next_el.save(update_fields=["entitled"])
                LeaveTransaction.objects.create(
                    user_id=uid, year=next_year, category=LeaveCategory.EL.value,
                    amount=total_credit, reason=LeaveTransaction.CONVERSION)

            if col_cf > 0:
                next_col, _ = LeaveBalance.objects.get_or_create(
                    user_id=uid, year=next_year, category=LeaveCategory.COL.value,
                    defaults={"entitled": Decimal("0")})
                next_col.entitled += col_cf
                next_col.save(update_fields=["entitled"])
                LeaveTransaction.objects.create(
                    user_id=uid, year=next_year, category=LeaveCategory.COL.value,
                    amount=col_cf, reason=LeaveTransaction.OPENING)

            processed_count += 1
    return {"users_processed": processed_count}
