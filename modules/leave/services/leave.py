"""All ELM writes. Transactions, audit rows, and domain→HTTP translation.

A service raises a *domain* error (core.api.exceptions), never a DRF one, so it
stays callable from a Celery task or a management command.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave import selectors
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain.categories import LeaveCategory
from modules.leave.domain.day_counting import (
    InvalidLeavePeriod,
    count_leave_days,
)
from modules.leave.models import (
    LeaveAccount,
    LeaveApplication,
    LeaveTransition,
    SubstituteNomination,
    YearEndRun,
)

ZERO = Decimal("0")
#: Statuses that block a new overlapping request (ELM Problem Statement §5).
BLOCKING = ("pending", "recommended", "not_recommended", "sanctioned")


def _account(user_id: int, category: str, year: int) -> LeaveAccount:
    default_entitlement = Decimal("0")
    try:
        cat_enum = LeaveCategory(category)
        default_entitlement = cat.CATEGORY_RULES.get(
            cat_enum, {}).get("annual_entitlement", Decimal("0"))
    except (ValueError, KeyError):
        pass
    acct, _ = LeaveAccount.objects.get_or_create(
        user_id=user_id, category=category, year=year,
        defaults={"entitlement": default_entitlement})
    return acct


def _record(application, frm: str, to: str, *, actor_user_id, actor_role,
            reason: str = "") -> None:
    LeaveTransition.objects.create(
        application=application, from_status=frm, to_status=to,
        actor_user_id=actor_user_id, actor_role=actor_role, reason=reason)


def _overlaps(user_id: int, starts_on: date, ends_on: date, half_day: str,
              exclude_id: int | None = None) -> bool:
    """Impermissible overlap with the employee's active leave. First-half and
    second-half CL on the same date do NOT overlap (§5)."""
    qs = LeaveApplication.objects.filter(
        applicant_user_id=user_id, status__in=BLOCKING,
        starts_on__lte=ends_on, ends_on__gte=starts_on)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    for other in qs:
        if other.starts_on == other.ends_on == starts_on == ends_on:
            from modules.leave.domain.day_counting import half_day_overlaps
            if not half_day_overlaps(half_day, other.half_day):
                continue
        return True
    return False


def _require_vacation(starts_on: date, ends_on: date) -> None:
    for v in selectors.active_vacations():
        if v.starts_on <= starts_on and ends_on <= v.ends_on:
            return
    raise ConflictError(
        "VL may be availed only within a published vacation period.")


def _require_restricted_holiday(starts_on: date, ends_on: date) -> None:
    rh = selectors.restricted_holiday_dates()
    day = starts_on
    while day <= ends_on:
        if day in rh:
            return
        day = date.fromordinal(day.toordinal() + 1)
    raise ConflictError(
        "An RH request must correspond to a published restricted holiday.")


@transaction.atomic
def apply_leave(*, principal, category, starts_on, ends_on, purpose="",
                half_day="none", station_leave=False,
                station_leave_place="", station_leave_reason="",
                substitute_user_id=None) -> LeaveApplication:
    try:
        category = LeaveCategory(category)
    except ValueError:
        raise BadRequestError(f"Unknown leave category {category!r}.") from None
    if ends_on < starts_on:
        raise BadRequestError("The leave period ends before it starts.")
    if station_leave and not station_leave_place:
        raise BadRequestError("Station Leave requires a place.")

    holidays = selectors.closed_holiday_dates()
    try:
        leave_days = count_leave_days(category=category, starts_on=starts_on,
                                      ends_on=ends_on, closed_holidays=holidays,
                                      half_day=half_day)
    except InvalidLeavePeriod as exc:
        raise BadRequestError(str(exc)) from exc

    if category is LeaveCategory.VL:
        _require_vacation(starts_on, ends_on)
    if category is LeaveCategory.RH:
        _require_restricted_holiday(starts_on, ends_on)

    if _overlaps(principal.user_id, starts_on, ends_on, half_day):
        raise ConflictError(
            "This period overlaps an active pending or approved request.")

    year = starts_on.year
    acct = _account(principal.user_id, category.value, year)
    if acct.remaining < leave_days and cat.carries_forward(category):
        raise ConflictError("Insufficient balance for this request.")

    application = LeaveApplication.objects.create(
        applicant_user_id=principal.user_id, category=category.value,
        starts_on=starts_on, ends_on=ends_on, half_day=half_day,
        purpose=purpose, leave_days=leave_days, status=sm.PENDING,
        station_leave=station_leave, station_leave_place=station_leave_place,
        station_leave_reason=station_leave_reason)

    if substitute_user_id:
        if substitute_user_id == principal.user_id:
            raise BadRequestError("The applicant cannot be their own substitute.")
        SubstituteNomination.objects.create(
            application=application, substitute_user_id=substitute_user_id)

    _record(application, "", sm.PENDING, actor_user_id=principal.user_id,
            actor_role="applicant")
    return application


@transaction.atomic
def withdraw(*, application_id: int, principal) -> LeaveApplication:
    app = (LeaveApplication.objects.select_for_update()
           .filter(pk=application_id, applicant_user_id=principal.user_id)
           .first())
    if app is None:
        raise NotFoundError("No such leave request.")
    if not sm.may_withdraw(app.status):
        raise ConflictError(
            "Only a request that has not been finally approved can be withdrawn.")
    frm, app.status = app.status, sm.WITHDRAWN
    app.save(update_fields=["status", "updated_at"])
    _record(app, frm, sm.WITHDRAWN, actor_user_id=principal.user_id,
            actor_role="applicant")
    return app


@transaction.atomic
def decide(*, application_id: int, principal, actor_role: str, to_status: str,
           reason: str = "") -> LeaveApplication:
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    sm.validate_transition(app.status, to_status, actor=actor_role,
                           permissions=frozenset(principal.permissions))
    if actor_role == "unit_head" and to_status in (sm.SANCTIONED, sm.REJECTED):
        fa = cat.final_authority(LeaveCategory(app.category))
        if fa != cat.FinalAuthority.UNIT_HEAD:
            raise ConflictError("Unit head cannot sanction or reject this category directly.")
    frm = app.status
    if to_status == sm.SANCTIONED and frm != sm.CANCELLATION_PENDING:
        acct = _account(app.applicant_user_id, app.category, app.starts_on.year)
        if acct.remaining < app.leave_days:
            raise ConflictError("Insufficient balance to sanction this request.")
        acct.availed = acct.availed + app.leave_days
        acct.save(update_fields=["availed", "updated_at"])
    app.status = to_status
    app.decision_note = reason
    app.decided_at = timezone.now()
    if actor_role == "unit_head":
        app.unit_head_user_id = principal.user_id
    else:
        app.sanction_authority_user_id = principal.user_id
    app.save(update_fields=["status", "decision_note", "decided_at",
                            "unit_head_user_id", "sanction_authority_user_id",
                            "updated_at"])
    if to_status == sm.CANCELLED and app.resumption_on is None:
        # Cancellation restores the earlier sanctioned deduction (§8).
        acct = _account(app.applicant_user_id, app.category, app.starts_on.year)
        acct.availed = max(ZERO, acct.availed - app.leave_days)
        acct.save(update_fields=["availed", "updated_at"])
    _record(app, frm, to_status, actor_user_id=principal.user_id,
            actor_role=actor_role, reason=reason)
    return app


@transaction.atomic
def request_cancellation(*, application_id: int, principal,
                         reason: str = "") -> LeaveApplication:
    app = (LeaveApplication.objects.select_for_update()
           .filter(pk=application_id, applicant_user_id=principal.user_id)
           .first())
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status != sm.SANCTIONED:
        raise ConflictError("Only an approved leave can be cancelled.")
    if app.starts_on <= timezone.localdate():
        raise ConflictError(
            "Once leave has begun, use the extension or resumption process.")
    frm, app.status = app.status, sm.CANCELLATION_PENDING
    app.save(update_fields=["status", "updated_at"])
    _record(app, frm, sm.CANCELLATION_PENDING, actor_user_id=principal.user_id,
            actor_role="applicant", reason=reason)
    return app


@transaction.atomic
def request_extension(*, application_id: int, principal, ends_on: date,
                      reason: str = "") -> LeaveApplication:
    app = (LeaveApplication.objects.select_for_update()
           .filter(pk=application_id, applicant_user_id=principal.user_id)
           .first())
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status != sm.SANCTIONED:
        raise ConflictError("Only an ongoing approved leave can be extended.")
    if app.category not in (LeaveCategory.EL.value, LeaveCategory.COL.value,
                            LeaveCategory.VL.value):
        raise ConflictError("Extensions apply to EL, COL and VL only.")
    if ends_on <= app.ends_on:
        raise BadRequestError("An extension must extend the approved end date.")
    frm, app.status = app.status, sm.EXTENSION_PENDING
    app.save(update_fields=["status", "updated_at"])
    _record(app, frm, sm.EXTENSION_PENDING, actor_user_id=principal.user_id,
            actor_role="applicant", reason=reason)
    return app


@transaction.atomic
def report_resumption(*, application_id: int, principal,
                      resumption_on: date) -> LeaveApplication:
    app = (LeaveApplication.objects.select_for_update()
           .filter(pk=application_id, applicant_user_id=principal.user_id)
           .first())
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status != sm.SANCTIONED:
        raise ConflictError("Resumption applies to sanctioned EL, COL or VL only.")
    app.resumption_on = resumption_on
    frm, app.status = app.status, sm.RESUMPTION_PENDING
    app.save(update_fields=["resumption_on", "status", "updated_at"])
    _record(app, frm, sm.RESUMPTION_PENDING, actor_user_id=principal.user_id,
            actor_role="applicant")
    return app


@transaction.atomic
def record_offline_leave(*, principal, applicant_user_id: int, category,
                         starts_on: date, ends_on: date, reference: str,
                         purpose: str = "") -> LeaveApplication:
    """Synchronise leave already sanctioned through a valid paper/offline route
    (§12). Not a second approval workflow: it lands as sanctioned and updates
    the balance, with the sanction reference captured as evidence."""
    if not reference:
        raise BadRequestError("An offline sanction reference is required.")
    try:
        category = LeaveCategory(category)
    except ValueError:
        raise BadRequestError(f"Unknown leave category {category!r}.") from None
    holidays = selectors.closed_holiday_dates()
    try:
        leave_days = count_leave_days(category=category, starts_on=starts_on,
                                      ends_on=ends_on, closed_holidays=holidays)
    except InvalidLeavePeriod as exc:
        raise BadRequestError(str(exc)) from exc
    app = LeaveApplication.objects.create(
        applicant_user_id=applicant_user_id, category=category.value,
        starts_on=starts_on, ends_on=ends_on, purpose=purpose,
        leave_days=leave_days, status=sm.SANCTIONED,
        decision_note=f"Offline sanction: {reference}",
        decided_at=timezone.now())
    acct = _account(applicant_user_id, category.value, starts_on.year)
    acct.availed = acct.availed + leave_days
    acct.save(update_fields=["availed", "updated_at"])
    _record(app, "", sm.SANCTIONED, actor_user_id=principal.user_id,
            actor_role="leave_administrator", reason=reference)
    return app


@transaction.atomic
def respond_to_cover(*, application_id: int, principal, accept: bool):
    """The nominated substitute accepts or declines (§6). Required consent must
    be accepted before approval routing continues."""
    sub = (SubstituteNomination.objects.select_for_update()
           .filter(application_id=application_id,
                   substitute_user_id=principal.user_id).first())
    if sub is None:
        raise NotFoundError("No outstanding cover request for you.")
    sub.status = "accepted" if accept else "declined"
    sub.responded_at = timezone.now()
    sub.save(update_fields=["status", "responded_at", "updated_at"])
    return sub


def leave_statistics() -> dict:
    from django.db.models import Count

    by_status = dict(
        LeaveApplication.objects.values_list("status")
        .annotate(n=Count("pk")).values_list("status", "n"))
    by_category = dict(
        LeaveApplication.objects.values_list("category")
        .annotate(n=Count("pk")).values_list("category", "n"))
    return {"by_status": by_status, "by_category": by_category}


def process_year_end(year: int, *, now: datetime | None = None) -> YearEndRun:
    """Apply year-end outcomes (§13, EL-UC-020). Reports an exception rather
    than committing an uncertain adjustment."""
    now = now or timezone.now()
    exceptions: list[str] = []
    processed = 0
    for acct in LeaveAccount.objects.filter(year=year):
        try:
            outcome = cat.year_end_outcome(LeaveCategory(acct.category))
        except ValueError:
            exceptions.append(f"account {acct.pk}: unknown category")
            continue
        remaining = acct.remaining
        if outcome == cat.YearEndOutcome.LAPSE:
            acct.entitlement = ZERO
            acct.carried_forward = ZERO
        elif outcome == cat.YearEndOutcome.CONVERT_TO_EL:
            converted = cat.convert_vl_to_el(remaining)
            next_el, _ = LeaveAccount.objects.get_or_create(
                user_id=acct.user_id, category=LeaveCategory.EL.value,
                year=year + 1)
            next_el.carried_forward = next_el.carried_forward + converted
            next_el.save(update_fields=["carried_forward", "updated_at"])
            acct.entitlement = ZERO
            acct.carried_forward = ZERO
        elif outcome == cat.YearEndOutcome.CARRY_FORWARD:
            nxt, _ = LeaveAccount.objects.get_or_create(
                user_id=acct.user_id, category=acct.category, year=year + 1)
            nxt.carried_forward = nxt.carried_forward + remaining
            nxt.save(update_fields=["carried_forward", "updated_at"])
        acct.save(update_fields=["entitlement", "carried_forward", "updated_at"])
        processed += 1
    return YearEndRun.objects.create(year=year, processed_accounts=processed,
                                     exceptions=exceptions, ran_at=now)


def run_sla_sweep(*, now: datetime | None = None) -> int:
    """Pending-only reminder/escalation for actionable tasks (§14, EL-UC-021)."""
    now = now or timezone.now()
    touched = 0
    for task in selectors.open_tasks():
        if task.due_at and task.due_at <= now:
            if task.reminded_at is None:
                task.reminded_at = now
                task.save(update_fields=["reminded_at", "updated_at"])
            elif task.escalated_at is None:
                task.escalated_at = now
                task.save(update_fields=["escalated_at", "updated_at"])
            touched += 1
    return touched
