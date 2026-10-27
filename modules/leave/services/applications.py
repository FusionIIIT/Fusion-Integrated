"""Leave application lifecycle operations (apply and transition)."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import rules
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)

log = logging.getLogger("fusion.leave.applications")


def actor_kind(actor, application=None, role: str | None = None) -> str:
    """Which lane of the state machine this caller is in."""
    if actor is None:
        return sm.SYSTEM
    if role:
        return role
    if getattr(actor, "actor_kind", None):
        return actor.actor_kind
    user_id = getattr(actor, "user_id", None)
    if application is not None:
        if application.applicant_is_director and user_id == application.user_id and \
                application.status == sm.AWAITING_DIRECTOR_SELF_SANCTION:
            return sm.DIRECTOR
        if application.substitute_user_id == user_id and \
                application.status == sm.AWAITING_SUBSTITUTE:
            return sm.SUBSTITUTE
    roles = {r.lower() for r in getattr(actor, "roles", ())}
    if "director" in roles:
        return sm.DIRECTOR
    if "authority" in roles or "dean" in roles or "registrar" in roles:
        return sm.AUTHORITY
    if "establishment" in roles:
        return sm.ESTABLISHMENT
    if "unit_head" in roles or "hod" in roles:
        return sm.UNIT_HEAD
    if getattr(actor, "has_permission", lambda p: False)(
        "leave_management.application.review"
    ):
        if application is not None:
            if application.status in (
                sm.AWAITING_UNIT_HEAD, sm.CANCELLATION_PENDING_UNIT_HEAD
            ):
                return sm.UNIT_HEAD
            if application.status in (
                sm.AWAITING_ESTABLISHMENT, sm.CANCELLATION_PENDING_ESTABLISHMENT
            ):
                return sm.ESTABLISHMENT
            if application.status in (
                sm.AWAITING_FINAL_SANCTION, sm.CANCELLATION_PENDING_FINAL
            ):
                return sm.AUTHORITY
            if application.status == sm.AWAITING_DIRECTOR_SELF_SANCTION:
                return sm.DIRECTOR
        return sm.UNIT_HEAD
    if getattr(actor, "has_permission", lambda p: False)(
        "leave_management.application.respond"
    ):
        return sm.SUBSTITUTE
    return sm.EMPLOYEE


def resolve_or_raise(frm: str, to: str, kind: str, category_code: str) -> sm.Transition:
    """Resolves a transition or raises a domain error if invalid."""
    try:
        return sm.resolve(frm, to, actor_kind=kind, category_code=category_code)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"An application cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition"
        ) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed"
        ) from exc
    except sm.ScopeMismatch as exc:
        raise ConflictError(
            f"Category '{exc.category_code}' cannot make this transition "
            f"(scope '{exc.scope}').", code="scope_mismatch"
        ) from exc


@transaction.atomic
def apply(*, user_id: int, category_code: str, start_date: date, end_date: date,
               half_day: str = "", reason: str = "", is_station_leave: bool = False,
               station_details: dict | None = None, substitute_user_id: int | None = None,
               applicant_is_director: bool = False, medical_evidence_ref: str = "",
               holidays: Sequence[date] = ()) -> LeaveApplication:
    """Creates and submits a new leave application."""
    if end_date < start_date:
        raise ConflictError("end_date must be on or after start_date.", code="invalid_dates")
    if not (reason or "").strip():
        raise ConflictError("A reason is required.", code="reason_required")
    if half_day:
        if category_code != "CL":
            raise ConflictError(
                "Half-day is only permitted for Casual Leave (CL).",
                code="half_day_not_allowed"
            )
        if start_date != end_date:
            raise ConflictError(
                "Half-day leave must be on a single day.", code="half_day_multi_day"
            )

    half_day_val = half_day if half_day in ("first", "second") else None

    try:
        category = LeaveCategory.objects.get(code=category_code)
    except LeaveCategory.DoesNotExist as exc:
        raise NotFoundError(f"Leave category {category_code} not found.") from exc

    days = rules.calculate_leave_days(
        category_code, start_date, end_date, half_day=half_day_val,
        holidays=frozenset(holidays) if holidays else frozenset()
    )
    days_charged = Decimal(str(days))

    # Overlap check
    qs = LeaveApplication.objects.filter(user_id=user_id).exclude(
        status__in=sm.TERMINAL
    )
    existing_leaves = [
        (
            existing.start_date,
            existing.end_date,
            existing.half_day if existing.half_day in ("first", "second") else None,
        )
        for existing in qs
    ]
    if rules.check_overlap(existing_leaves, start_date, end_date, half_day_val):
        raise ConflictError(
            "Application overlaps with an existing active leave.",
            code="leave_overlap"
        )

    # Balance check
    try:
        balance = LeaveBalance.objects.filter(
            user_id=user_id, category=category, year=start_date.year
        ).select_for_update().first()
    except LeaveBalance.DoesNotExist:
        balance = None

    if balance is not None and not rules.has_sufficient_balance(
        balance.balance_days, days_charged
    ):
        raise ConflictError("Insufficient leave balance.", code="insufficient_balance")

    # Initial state
    init_status = sm.initial_state(
        substitute_required=bool(substitute_user_id),
        applicant_is_director=applicant_is_director
    )

    # Create application
    app = LeaveApplication.objects.create(
        user_id=user_id, category=category, start_date=start_date,
        end_date=end_date, half_day=half_day or "", days_charged=days_charged,
        balance_deducted=Decimal("0.0"), reason=reason,
        is_station_leave=is_station_leave, station_details=station_details or {},
        substitute_user_id=substitute_user_id,
        applicant_is_director=applicant_is_director,
        medical_evidence_ref=medical_evidence_ref,
        status=init_status
    )

    # Create transition audit
    LeaveApplicationTransition.objects.create(
        application=app, from_status="", to_status=init_status,
        actor_user_id=user_id, actor_label=sm.EMPLOYEE, reason="Applied"
    )

    return app


@transaction.atomic
def transition(*, application_id: int, to_status: str, actor, reason: str = "",
               scope=None, recommendation: str = "", role: str | None = None,
               replacement_substitute_id: int | None = None) -> LeaveApplication:
    """Moves an application to a new status."""
    qs = scope if scope is not None else LeaveApplication.objects.all()
    app = qs.select_for_update().select_related("category").filter(
        pk=application_id
    ).first()
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app, role=role)
    t = resolve_or_raise(app.status, to_status, kind, app.category.code)

    if actor and getattr(actor, "has_permission", None) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(
            f"This action needs {t.permission}.", code="permission_denied"
        )

    # Guards
    if t.guards:
        for g in t.guards:
            if g == "has_reason" and not (reason or "").strip():
                raise ConflictError("A reason is required for this decision.",
                                    code="reason_required")
            if g == "before_start_date" and timezone.localdate() >= app.start_date:
                raise ConflictError(
                    "Approved leave may only be cancelled before its start date.",
                    code="leave_already_started"
                )
            if g == "recommendation_recorded":
                if recommendation:
                    app.recommendation = recommendation
                if app.recommendation not in ("recommended", "not_recommended"):
                    raise ConflictError("A recommendation is required.",
                                        code="recommendation_required")
            if g == "substitute_accepts_non_director":
                app.substitute_response = "accepted"
            if g == "substitute_accepts_director_applicant":
                app.substitute_response = "accepted"
            if g == "substitute_declines":
                app.substitute_response = "declined"
            if g == "eligible_replacement_nominated":
                if replacement_substitute_id:
                    app.substitute_user_id = replacement_substitute_id
                app.substitute_response = "pending"

    # Balance adjustments
    if to_status == sm.APPROVED and app.status != sm.APPROVED:
        try:
            bal = LeaveBalance.objects.select_for_update().filter(
                user_id=app.user_id, category=app.category, year=app.start_date.year
            ).first()
        except LeaveBalance.DoesNotExist:
            bal = None

        if bal is not None:
            if not rules.has_sufficient_balance(
                bal.balance_days, app.days_charged
            ):
                raise ConflictError(
                    "Insufficient leave balance to approve application.",
                    code="insufficient_balance"
                )
            bal.balance_days -= app.days_charged
            bal.save(update_fields=["balance_days", "updated_at"])
        app.balance_deducted = app.days_charged

    if to_status == sm.CANCELLED and app.status in (
        sm.CANCELLATION_PENDING_UNIT_HEAD, sm.CANCELLATION_PENDING_FINAL
    ):
        try:
            bal = LeaveBalance.objects.select_for_update().filter(
                user_id=app.user_id, category=app.category, year=app.start_date.year
            ).first()
        except LeaveBalance.DoesNotExist:
            bal = None

        if bal is not None and app.balance_deducted > Decimal("0.0"):
            bal.balance_days += app.balance_deducted
            bal.save(update_fields=["balance_days", "updated_at"])
        app.balance_deducted = Decimal("0.0")

    if to_status == sm.WITHDRAWN and reason:
        app.withdrawn_reason = reason[:300]

    # Update status
    frm = app.status
    app.status = to_status
    app.save()

    # Audit transition
    LeaveApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None), actor_label=kind,
        reason=reason
    )
    return app
