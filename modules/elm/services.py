"""Transactional workflows for the ELM bounded context."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.elm.domain.rules import (
    ACTIVE_REQUEST_STATUSES, CONTINUOUS_CATEGORIES, DEFAULT_ENTITLEMENTS,
    SUPPORTED_CATEGORIES, count_leave_days,
)
from modules.elm.models import (
    LeaveApplication, LeaveBalance, LeaveCalendar, LeaveCalendarDate,
    LeaveHierarchy, LeaveLedgerEntry, LeaveNotice, LeavePolicy, LeaveSLAConfig,
    LeaveSLAEvent, LeaveYearEndRun, VacationPeriod,
)


# "action_required" stays active for overlap/withdrawal checks, but is not an
# assigned-review SLA task until it has been resubmitted/rerouted.
PENDING_STATUSES = tuple(s for s in ACTIVE_REQUEST_STATUSES if s != "action_required")
OVERLAP_STATUSES = (*ACTIVE_REQUEST_STATUSES, "approved")


def _profile(actor):
    """Read employee kind and unit from the platform directory contract."""
    try:
        return directory.get_users([actor.user_id]).get(actor.user_id)
    except IamUnavailable:
        return None


def _employee_kind(actor) -> str:
    kind = getattr(actor, "kind", "")
    if kind not in {"faculty", "staff"}:
        raise PermissionDenied("ELM is available only to institute faculty and staff.")
    return kind


def _policy(category: str) -> LeavePolicy:
    policy = LeavePolicy.objects.filter(category=category).first()
    if policy is None:
        # Normally seeded by the initial migration; safe fallback for test DBs.
        kind = "faculty" if category == "VL" else "staff" if category == "EL" else "all"
        policy, _ = LeavePolicy.objects.get_or_create(
            category=category,
            defaults={
                "annual_entitlement": DEFAULT_ENTITLEMENTS[category],
                "employee_scope": kind,
                "carry_forward": category in {"EL", "COL"},
                "continuous_counting": category in CONTINUOUS_CATEGORIES,
                "medical_evidence_required": category == "COL",
            },
        )
    if not policy.enabled:
        raise ValidationError({"category": f"{category} is currently disabled by ELM policy."})
    return policy


def _eligible(policy: LeavePolicy, employee_kind: str) -> bool:
    return policy.employee_scope == "all" or policy.employee_scope == employee_kind


def _calendar_dates(start: date, end: date):
    # More than one year may remain published. Use each year's calendar so
    # cross-year leave requests retain the correct closures and holidays.
    calendars = LeaveCalendar.objects.filter(
        status="published",
        year__gte=start.year,
        year__lte=end.year,
    )
    rows = LeaveCalendarDate.objects.filter(
        calendar__in=calendars,
        day__range=(start, end),
    )
    return ({row.day for row in rows if row.is_closed_day},
            {row.day for row in rows if row.is_restricted_holiday})


def _days_by_year(category, start, end, cl_half="none") -> dict[str, str]:
    result: dict[str, str] = {}
    for year in range(start.year, end.year + 1):
        segment_start = max(start, date(year, 1, 1))
        segment_end = min(end, date(year, 12, 31))
        closed, _ = _calendar_dates(segment_start, segment_end)
        half = cl_half if start.year == end.year == year else "none"
        policy = LeavePolicy.objects.filter(category=category).first()
        continuous_counting = policy.continuous_counting if policy is not None else None
        units = count_leave_days(
            category, segment_start, segment_end, closed, half, continuous_counting,
        )
        if units > 0:
            result[str(year)] = str(units.quantize(Decimal("0.01")))
    return result


def _balance(user_id, employee_kind, year, category) -> LeaveBalance:
    # Disabled policies block new applications, not reads or year-end
    # carry-forward of balances that employees have already accrued.
    policy = LeavePolicy.objects.filter(category=category).first()
    if policy is None:
        policy = _policy(category)
    eligible = _eligible(policy, employee_kind)
    entitlement = policy.annual_entitlement if eligible and policy.enabled else Decimal("0.00")
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, employee_kind=employee_kind, year=year, category=category,
        defaults={"entitlement": entitlement},
    )
    # Existing accounts retain a policy snapshot for this year. New settings
    # affect balances created after a configuration change, not past ledgers.
    return balance


def _assert_available(user_id, employee_kind, days_by_year, category):
    for year_text, units_text in days_by_year.items():
        balance = _balance(user_id, employee_kind, int(year_text), category)
        balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
        # Pending applications reserve their requested units even before approval.
        # Approved applications are already reflected in balance.consumed.
        pending = LeaveApplication.objects.filter(
            applicant_user_id=user_id,
            employee_kind=employee_kind,
            category=category,
            status__in=ACTIVE_REQUEST_STATUSES,
            request_type__in=("leave", "extension", "offline"),
        )
        reserved = sum(
            (Decimal(app.requested_days_by_year.get(year_text, "0")) for app in pending),
            Decimal("0"),
        )
        available = balance.available - reserved
        if available < Decimal(units_text):
            raise ValidationError({
                "period": (f"Insufficient {category} balance in {year_text}: "
                           f"{available} day(s) available after pending requests, {units_text} requested.")
            })


def _overlaps(user_id, start, end, category, cl_half, exclude_id=None):
    qs = LeaveApplication.objects.filter(
        applicant_user_id=user_id, status__in=OVERLAP_STATUSES,
        request_type__in=("leave", "extension", "offline"),
        start_date__lte=end, end_date__gte=start,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    for existing in qs:
        if (category == "CL" and existing.category == "CL" and start == end
                and existing.start_date == existing.end_date == start
                and cl_half != "none" and existing.cl_half != "none"
                and cl_half != existing.cl_half):
            continue
        return existing
    return None


def _route_fields(department: str, category: str, director_case: bool = False, force_higher_sanction: bool = False):
    hierarchy = LeaveHierarchy.objects.filter(unit_key=department, active=True).first()
    if hierarchy is None:
        raise ValidationError({
            "department": f"No active ELM hierarchy is configured for unit '{department or 'unknown'}'."
        })
    if director_case and not hierarchy.director_user_id:
        raise ValidationError({"routing": "No Director is configured for this leave request."})
    if not director_case and not hierarchy.unit_head_user_id:
        raise ValidationError({"routing": f"No Unit Head is configured for unit '{department or 'unknown'}'."})
    if not director_case and (category not in {"CL", "RH"} or force_higher_sanction) and not hierarchy.sanctioning_authority_user_id:
        raise ValidationError({"routing": f"No sanctioning authority is configured for unit '{department or 'unknown'}'."})
    fields = {
        "unit_head_user_id": hierarchy.unit_head_user_id,
        "establishment_user_id": hierarchy.establishment_user_id,
        "sanctioning_authority_user_id": hierarchy.sanctioning_authority_user_id,
    }
    if director_case:
        fields["current_assignee_user_id"] = hierarchy.director_user_id if hierarchy else None
        fields["status"] = "awaiting_sanction"
    elif category in {"CL", "RH"}:
        fields["current_assignee_user_id"] = fields["unit_head_user_id"]
        fields["status"] = "awaiting_unit_head"
    else:
        fields["current_assignee_user_id"] = fields["unit_head_user_id"]
        fields["status"] = "awaiting_unit_head"
    return fields


def _notify(user_id, app, kind, message):
    if user_id:
        LeaveNotice.objects.create(user_id=user_id, application=app, kind=kind, message=message)


def _record(app, actor_user_id, action, from_status, to_status, note=""):
    # Store history in the existing ledger-like notice trail through an internal
    # transition entry; the dedicated model keeps workflow history queryable.
    from modules.elm.models import LeaveTransition
    LeaveTransition.objects.create(application=app, actor_user_id=actor_user_id,
                                   action=action, from_status=from_status,
                                   to_status=to_status, note=note)


def _transition(app, actor_user_id, status, action, note="", assignee=None):
    old = app.status
    app.status = status
    app.current_assignee_user_id = assignee
    app.save(update_fields=["status", "current_assignee_user_id", "updated_at"])
    _record(app, actor_user_id, action, old, status, note)
    _notify(assignee, app, "task_assigned", f"ELM action required: {action.replace('_', ' ')}.")


def _post_balance_change(app, actor_user_id, year, category, units, entry_type, reference_suffix, note=""):
    units = Decimal(units)
    balance = _balance(app.applicant_user_id, app.employee_kind, int(year), category)
    if entry_type == "debit":
        balance.consumed += units
    elif entry_type == "restore":
        balance.consumed = max(Decimal("0.00"), balance.consumed - units)
    elif entry_type == "lapse":
        balance.lapsed += units
    elif entry_type == "convert_out":
        balance.converted_out += units
    elif entry_type == "convert_in":
        balance.converted_in += units
    elif entry_type == "carry_forward":
        balance.carried_in += units
    elif entry_type == "credit":
        balance.converted_in += units
    balance.save()
    LeaveLedgerEntry.objects.get_or_create(
        reference_key=f"app:{app.pk}:{reference_suffix}:{year}:{category}",
        defaults={"user_id": app.applicant_user_id, "employee_kind": app.employee_kind,
                  "year": int(year), "category": category, "entry_type": entry_type,
                  "units": units, "application": app, "actor_user_id": actor_user_id,
                  "note": note},
    )


def post_application_balance(app: LeaveApplication, actor_user_id: int):
    """Post only the accepted new/extension period; idempotency is ledger keyed."""
    with transaction.atomic():
        for year_text, units in app.requested_days_by_year.items():
            key = f"app:{app.pk}:debit:{year_text}:{app.category}"
            if LeaveLedgerEntry.objects.filter(reference_key=key).exists():
                continue
            balance = _balance(app.applicant_user_id, app.employee_kind, int(year_text), app.category)
            balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
            amount = Decimal(units)
            if app.request_type != "offline" and balance.available < amount:
                raise ValidationError({
                    "balance": (
                        f"Insufficient {app.category} balance for year {year_text} "
                        "at approval time. Refresh the request and balance before retrying."
                    )
                })
            balance.consumed += amount
            balance.save(update_fields=["consumed", "updated_at"])
            LeaveLedgerEntry.objects.create(
                user_id=app.applicant_user_id, employee_kind=app.employee_kind,
                year=int(year_text), category=app.category, entry_type="debit", units=amount,
                application=app, reference_key=key, actor_user_id=actor_user_id,
                note=f"Approved {app.request_type} request",
            )


@transaction.atomic
def create_leave_application(actor, data):
    employee_kind = _employee_kind(actor)
    category = data["category"]
    if category not in SUPPORTED_CATEGORIES:
        raise ValidationError({"category": "Choose CL, RH, SCL, EL, COL, or VL."})
    start, end = data["start_date"], data["end_date"]
    policy = _policy(category)
    if not _eligible(policy, employee_kind):
        raise ValidationError({"category": f"{category} is not applicable to {employee_kind}."})
    if policy.medical_evidence_required and not data.get("evidence_reference"):
        raise ValidationError({"evidence_reference": "Supporting medical evidence/reference is required by current policy."})
    closed, restricted = _calendar_dates(start, end)
    if category == "RH" and start not in restricted:
        raise ValidationError({"start_date": "RH must match a Restricted Holiday in the currently published calendar."})
    if category == "VL" and not VacationPeriod.objects.filter(
        active=True, start_date__lte=start, end_date__gte=end,
    ).exists():
        raise ValidationError({"period": "VL must fall inside an active Academic Calendar vacation period."})
    try:
        days_by_year = _days_by_year(category, start, end, data.get("cl_half", "none"))
    except ValueError as exc:
        raise ValidationError({"period": str(exc)}) from exc
    total = sum((Decimal(v) for v in days_by_year.values()), Decimal("0.00"))
    if total <= 0:
        raise ValidationError({"period": "The selected period contains no countable leave days."})
    overlap = _overlaps(actor.user_id, start, end, category, data.get("cl_half", "none"))
    if overlap:
        raise ValidationError({"period": f"This overlaps active leave request EL-{overlap.pk}."})
    _assert_available(actor.user_id, employee_kind, days_by_year, category)

    profile = _profile(actor)
    department = (profile.department if profile else "") or ""
    needs_substitute = bool(data.get("requires_substitute"))
    substitute_id = data.get("substitute_user_id")
    if needs_substitute:
        if not substitute_id:
            raise ValidationError({"substitute_user_id": "Select an eligible substitute."})
        if int(substitute_id) == actor.user_id:
            raise ValidationError({"substitute_user_id": "The substitute must be another employee."})
        try:
            nominee = directory.get_users([int(substitute_id)]).get(int(substitute_id))
        except IamUnavailable as exc:
            raise ValidationError({"substitute_user_id": "The employee directory is unavailable; retry later."}) from exc
        if not nominee or nominee.kind not in {"faculty", "staff"}:
            raise ValidationError({"substitute_user_id": "The substitute must be an active faculty/staff employee."})
        collision = _overlaps(int(substitute_id), start, end, category, data.get("cl_half", "none"))
        if collision:
            raise ValidationError({"substitute_user_id": "The substitute has overlapping pending or approved leave."})
    active_role = (getattr(actor, "active_role", "") or "").lower()
    is_director = (
        "director" in {r.lower().replace(" ", "_") for r in (getattr(actor, "roles", ()) or ())}
        or active_role == "director"
    )
    routing = _route_fields(department, category, is_director)
    if needs_substitute:
        routing["status"] = "awaiting_substitute"
        routing["current_assignee_user_id"] = int(substitute_id)
    app = LeaveApplication.objects.create(
        applicant_user_id=actor.user_id, employee_kind=employee_kind, department=department,
        request_type="leave", category=category, start_date=start, end_date=end,
        cl_half=data.get("cl_half", "none"), requested_days=total,
        requested_days_by_year=days_by_year, purpose=data["purpose"],
        station_leave=data.get("station_leave", False),
        station_leave_details=data.get("station_leave_details", ""),
        requires_substitute=needs_substitute, substitute_user_id=int(substitute_id) if needs_substitute else None,
        substitute_response="pending" if needs_substitute else "not_required",
        evidence_reference=data.get("evidence_reference", ""),
        director_case=is_director, **routing,
    )
    _record(app, actor.user_id, "submitted", "draft", app.status)
    _notify(app.current_assignee_user_id, app, "task_assigned", "A leave request requires your action.")
    return app


def respond_substitute(actor, app, response):
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=app.pk)
        if app.status != "awaiting_substitute" or app.substitute_user_id != actor.user_id:
            raise PermissionDenied("This substitute request is not assigned to you or is no longer pending.")
        if response not in {"accept", "decline"}:
            raise ValidationError({"response": "Choose accept or decline."})
        app.substitute_response = "accepted" if response == "accept" else "declined"
        app.save(update_fields=["substitute_response", "updated_at"])
        if response == "accept":
            route = _route_fields(app.department, app.category, director_case=app.director_case)
            _transition(app, actor.user_id, route["status"], "substitute_accepted", assignee=route["current_assignee_user_id"])
            app.unit_head_user_id = route["unit_head_user_id"]
            app.establishment_user_id = route["establishment_user_id"]
            app.sanctioning_authority_user_id = route["sanctioning_authority_user_id"]
            app.save(update_fields=["unit_head_user_id", "establishment_user_id", "sanctioning_authority_user_id", "updated_at"])
        else:
            _transition(app, actor.user_id, "action_required", "substitute_declined", assignee=app.applicant_user_id)
        return app


@transaction.atomic
def retry_after_substitute_decline(actor, app, substitute_user_id=None):
    app = LeaveApplication.objects.select_for_update().get(pk=app.pk)
    if app.applicant_user_id != actor.user_id:
        raise PermissionDenied("Only the applicant may retry a declined substitute request.")
    if app.status != "action_required" or app.substitute_response != "declined":
        raise ValidationError({"status": "Only a request with a declined substitute can be retried."})

    if substitute_user_id is not None:
        try:
            substitute_user_id = int(substitute_user_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"substitute_user_id": "Must be a valid employee user ID."}) from exc
        if not 1 <= substitute_user_id <= 2147483647:
            raise ValidationError({"substitute_user_id": "Must be a positive 32-bit employee user ID."})
        if substitute_user_id == actor.user_id:
            raise ValidationError({"substitute_user_id": "The substitute must be another employee."})
        try:
            nominee = directory.get_users([substitute_user_id]).get(substitute_user_id)
        except IamUnavailable as exc:
            raise ValidationError({"substitute_user_id": "The employee directory is unavailable; retry later."}) from exc
        if not nominee or nominee.kind not in {"faculty", "staff"}:
            raise ValidationError({"substitute_user_id": "The substitute must be an active faculty/staff employee."})
        collision = _overlaps(
            substitute_user_id, app.start_date, app.end_date, app.category, app.cl_half,
        )
        if collision:
            raise ValidationError({"substitute_user_id": "The substitute has overlapping pending or approved leave."})
        app.requires_substitute = True
        app.substitute_user_id = substitute_user_id
        app.substitute_response = "pending"
        app.save(update_fields=["requires_substitute", "substitute_user_id", "substitute_response", "updated_at"])
        _transition(
            app, actor.user_id, "awaiting_substitute", "substitute_reassigned",
            "Applicant nominated a replacement substitute.", substitute_user_id,
        )
        return app

    route = _route_fields(app.department, app.category, director_case=app.director_case)
    app.requires_substitute = False
    app.substitute_user_id = None
    app.substitute_response = "not_required"
    app.unit_head_user_id = route["unit_head_user_id"]
    app.establishment_user_id = route["establishment_user_id"]
    app.sanctioning_authority_user_id = route["sanctioning_authority_user_id"]
    app.save(update_fields=[
        "requires_substitute", "substitute_user_id", "substitute_response",
        "unit_head_user_id", "establishment_user_id", "sanctioning_authority_user_id",
        "updated_at",
    ])
    _transition(
        app, actor.user_id, route["status"], "resubmitted_without_substitute",
        "Applicant continued without a substitute.", route["current_assignee_user_id"],
    )
    return app


def decide_request(actor, app, decision, note=""):
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().get(pk=app.pk)
        if not app.current_assignee_user_id and not actor.has_permission("elm.leave.manage"):
            raise PermissionDenied("This request has no assignee. An ELM administrator must resolve its routing.")
        if app.current_assignee_user_id and app.current_assignee_user_id != actor.user_id and not actor.has_permission("elm.leave.manage"):
            raise PermissionDenied("This request is not assigned to you.")
        if app.status in {"awaiting_unit_head", "awaiting_cancellation_unit_head"}:
            if app.category in {"CL", "RH"} and app.request_type in {"leave", "offline"}:
                if decision not in {"approve", "reject"}:
                    raise ValidationError({"decision": "Unit Head must approve or reject CL/RH."})
                if decision == "approve":
                    app.final_decision = "approved"
                    app.final_decided_at = timezone.now()
                    app.final_decision_note = note
                    app.save(update_fields=["final_decision", "final_decided_at", "final_decision_note", "updated_at"])
                    _transition(app, actor.user_id, "approved", "unit_head_approved", note)
                    post_application_balance(app, actor.user_id)
                else:
                    app.final_decision = "rejected"
                    app.final_decided_at = timezone.now()
                    app.final_decision_note = note
                    app.save(update_fields=["final_decision", "final_decided_at", "final_decision_note", "updated_at"])
                    _transition(app, actor.user_id, "rejected", "unit_head_rejected", note)
                _notify(app.applicant_user_id, app, "decision", f"Your ELM request was {app.status}.")
                return app
            if decision not in {"recommended", "not_recommended"}:
                raise ValidationError({"decision": "For higher-sanction leave, choose recommended or not_recommended."})
            app.unit_head_recommendation = decision
            next_assignee = app.establishment_user_id or app.sanctioning_authority_user_id
            next_status = "awaiting_establishment" if app.establishment_user_id else "awaiting_sanction"
            app.save(update_fields=["unit_head_recommendation", "updated_at"])
            _transition(app, actor.user_id, next_status, f"unit_head_{decision}", note, next_assignee)
            return app
        if app.status == "awaiting_establishment":
            if decision != "route":
                raise ValidationError({"decision": "Establishment verifies and routes; it does not make the final sanctioning decision here."})
            _transition(app, actor.user_id, "awaiting_sanction", "establishment_routed", note,
                        app.sanctioning_authority_user_id)
            return app
        if app.status in {"awaiting_sanction", "awaiting_cancellation_sanction", "awaiting_resumption_review"}:
            if app.status == "awaiting_resumption_review":
                if decision != "review":
                    raise ValidationError({"decision": "Choose review to complete the resumption review."})
                _apply_resumption_review(app, actor.user_id, note)
                return app
            if decision not in {"approve", "reject"}:
                raise ValidationError({"decision": "Choose approve or reject."})
            app.final_decision = "approved" if decision == "approve" else "rejected"
            app.final_decision_note = note
            app.final_decided_at = timezone.now()
            app.save(update_fields=["final_decision", "final_decision_note", "final_decided_at", "updated_at"])
            if app.request_type == "cancellation":
                if decision == "approve" and app.parent_application:
                    parent = app.parent_application
                    parent.status = "cancelled"
                    parent.save(update_fields=["status", "updated_at"])
                    for y, units in parent.requested_days_by_year.items():
                        key = f"app:{parent.pk}:restore:{y}:{parent.category}"
                        if not LeaveLedgerEntry.objects.filter(reference_key=key).exists():
                            balance = _balance(parent.applicant_user_id, parent.employee_kind, int(y), parent.category)
                            amount = Decimal(units)
                            balance.consumed = max(Decimal("0.00"), balance.consumed - amount)
                            balance.save(update_fields=["consumed", "updated_at"])
                            LeaveLedgerEntry.objects.create(user_id=parent.applicant_user_id,
                                employee_kind=parent.employee_kind, year=int(y), category=parent.category,
                                entry_type="restore", units=amount, application=parent, reference_key=key,
                                actor_user_id=actor.user_id, note="Approved cancellation restores balance")
                _transition(app, actor.user_id, "approved" if decision == "approve" else "rejected",
                            f"cancellation_{decision}", note)
            elif app.request_type == "extension":
                _transition(app, actor.user_id, "approved" if decision == "approve" else "rejected",
                            f"extension_{decision}", note)
                if decision == "approve":
                    post_application_balance(app, actor.user_id)
            else:
                _transition(app, actor.user_id, "approved" if decision == "approve" else "rejected",
                            f"sanction_{decision}", note)
                if decision == "approve":
                    post_application_balance(app, actor.user_id)
            _notify(app.applicant_user_id, app, "decision", f"Your ELM request was {app.status}.")
            return app
        raise ValidationError({"status": "This request has no decision available in its current state."})


def _apply_resumption_review(app, actor_user_id, note):
    parent = app.parent_application
    if parent is None or app.actual_resumption_date is None:
        raise ValidationError({"actual_resumption_date": "A related approved leave and actual resumption date are required."})
    actual_end = app.actual_resumption_date
    if actual_end != parent.end_date:
        new_by_year = _days_by_year(parent.category, parent.start_date, actual_end, parent.cl_half)
        old_by_year = parent.requested_days_by_year
        for year in set(old_by_year) | set(new_by_year):
            old_units = Decimal(old_by_year.get(year, "0"))
            new_units = Decimal(new_by_year.get(year, "0"))
            delta = new_units - old_units
            if delta > 0:
                balance = _balance(parent.applicant_user_id, parent.employee_kind, int(year), parent.category)
                balance.consumed += delta
                balance.save(update_fields=["consumed", "updated_at"])
                ref = f"app:{parent.pk}:resumption-adjust:{year}:{parent.category}"
                LeaveLedgerEntry.objects.get_or_create(reference_key=ref, defaults={
                    "user_id": parent.applicant_user_id, "employee_kind": parent.employee_kind,
                    "year": int(year), "category": parent.category, "entry_type": "debit",
                    "units": delta, "application": parent, "actor_user_id": actor_user_id,
                    "note": "Balance adjustment after reviewed late resumption"})
            elif delta < 0:
                amount = abs(delta)
                balance = _balance(parent.applicant_user_id, parent.employee_kind, int(year), parent.category)
                balance.consumed = max(Decimal("0"), balance.consumed - amount)
                balance.save(update_fields=["consumed", "updated_at"])
                ref = f"app:{parent.pk}:resumption-restore:{year}:{parent.category}"
                LeaveLedgerEntry.objects.get_or_create(reference_key=ref, defaults={
                    "user_id": parent.applicant_user_id, "employee_kind": parent.employee_kind,
                    "year": int(year), "category": parent.category, "entry_type": "restore",
                    "units": amount, "application": parent, "actor_user_id": actor_user_id,
                    "note": "Balance adjustment after reviewed early resumption"})
        parent.end_date = actual_end
        parent.requested_days_by_year = new_by_year
        parent.requested_days = sum((Decimal(v) for v in new_by_year.values()), Decimal("0"))
        parent.save(update_fields=["end_date", "requested_days_by_year", "requested_days", "updated_at"])
    _transition(app, actor_user_id, "approved", "resumption_reviewed", note)
    _notify(parent.applicant_user_id, app, "decision", "Your resumption review has been recorded.")


@transaction.atomic
def withdraw_request(actor, app, note=""):
    app = LeaveApplication.objects.select_for_update().get(pk=app.pk)
    if app.applicant_user_id != actor.user_id:
        raise PermissionDenied("You may withdraw only your own request.")
    if app.status not in ACTIVE_REQUEST_STATUSES:
        raise ValidationError({"status": "Only pending requests can be withdrawn."})
    previous_assignee = app.current_assignee_user_id
    _transition(app, actor.user_id, "withdrawn", "withdrawn", note)
    _notify(previous_assignee, app, "withdrawal", "The employee withdrew this ELM request.")
    return app


@transaction.atomic
def create_cancellation(actor, parent, reason=""):
    parent = LeaveApplication.objects.select_for_update().get(pk=parent.pk)
    if parent.applicant_user_id != actor.user_id or parent.status != "approved":
        raise ValidationError({"request": "Only your own approved leave can be requested for cancellation."})
    if parent.related_requests.filter(
        request_type="cancellation", status__in=ACTIVE_REQUEST_STATUSES,
    ).exists():
        raise ValidationError({"request": "A cancellation request is already pending for this leave."})
    if parent.start_date <= timezone.localdate():
        raise ValidationError({"request": "Approved leave can be cancelled only before it starts."})
    route = _route_fields(parent.department, parent.category, force_higher_sanction=True)
    if parent.category in {"CL", "RH"}:
        status, assignee = "awaiting_unit_head", route["unit_head_user_id"]
    else:
        status, assignee = "awaiting_unit_head", route["unit_head_user_id"]
    child = LeaveApplication.objects.create(
        applicant_user_id=parent.applicant_user_id, employee_kind=parent.employee_kind,
        department=parent.department, request_type="cancellation", parent_application=parent,
        category=parent.category, start_date=parent.start_date, end_date=parent.end_date,
        cl_half=parent.cl_half, requested_days=parent.requested_days,
        requested_days_by_year=parent.requested_days_by_year, purpose=parent.purpose,
        station_leave=parent.station_leave, station_leave_details=parent.station_leave_details,
        status=status, current_assignee_user_id=assignee,
        unit_head_user_id=route["unit_head_user_id"], establishment_user_id=route["establishment_user_id"],
        sanctioning_authority_user_id=route["sanctioning_authority_user_id"], action_reason=reason,
    )
    _record(child, actor.user_id, "cancellation_requested", "draft", status, reason)
    _notify(assignee, child, "task_assigned", "An approved-leave cancellation needs your review.")
    return child


@transaction.atomic
def create_extension(actor, parent, start, end, reason="", substitute_user_id=None):
    parent = LeaveApplication.objects.select_for_update().get(pk=parent.pk)
    if parent.applicant_user_id != actor.user_id or parent.status != "approved":
        raise ValidationError({"request": "Only your own approved leave can be extended."})
    if parent.category not in {"EL", "COL", "VL"}:
        raise ValidationError({"category": "Extensions are supported only for ongoing EL, COL, or VL."})
    if not (parent.start_date <= timezone.localdate() <= parent.end_date):
        raise ValidationError({"request": "Extension is available only while the original leave is ongoing."})
    if start <= parent.end_date or start > end:
        raise ValidationError({"period": "The extension must start after the existing approved end date."})
    overlap = _overlaps(parent.applicant_user_id, start, end, parent.category, "none")
    if overlap:
        raise ValidationError({"period": f"This overlaps active leave request EL-{overlap.pk}."})
    days_by_year = _days_by_year(parent.category, start, end)
    total = sum((Decimal(v) for v in days_by_year.values()), Decimal("0"))
    _assert_available(parent.applicant_user_id, parent.employee_kind, days_by_year, parent.category)
    director_case = parent.director_case
    route = _route_fields(parent.department, parent.category, director_case=director_case)
    needs_substitute = substitute_user_id is not None
    if needs_substitute:
        try:
            substitute_user_id = int(substitute_user_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"substitute_user_id": "Must be a valid employee user ID."}) from exc
        if substitute_user_id < 1 or substitute_user_id > 2147483647:
            raise ValidationError({"substitute_user_id": "Must be a positive 32-bit employee user ID."})
        if substitute_user_id == actor.user_id:
            raise ValidationError({"substitute_user_id": "The substitute must be another employee."})
        try:
            nominee = directory.get_users([substitute_user_id]).get(substitute_user_id)
        except IamUnavailable as exc:
            raise ValidationError({"substitute_user_id": "The employee directory is unavailable; retry later."}) from exc
        if not nominee or nominee.kind not in {"faculty", "staff"}:
            raise ValidationError({"substitute_user_id": "The substitute must be an active faculty/staff employee."})
        collision = _overlaps(substitute_user_id, start, end, parent.category, "none")
        if collision:
            raise ValidationError({"substitute_user_id": "The substitute has overlapping pending or approved leave."})
    child = LeaveApplication.objects.create(
        applicant_user_id=parent.applicant_user_id, employee_kind=parent.employee_kind,
        department=parent.department, request_type="extension", parent_application=parent,
        category=parent.category, start_date=start, end_date=end, requested_days=total,
        requested_days_by_year=days_by_year, purpose=parent.purpose,
        requires_substitute=needs_substitute, substitute_user_id=substitute_user_id,
        substitute_response="pending" if needs_substitute else "not_required",
        director_case=director_case,
        status="awaiting_substitute" if needs_substitute else route["status"],
        current_assignee_user_id=substitute_user_id if needs_substitute else route["current_assignee_user_id"],
        unit_head_user_id=route["unit_head_user_id"], establishment_user_id=route["establishment_user_id"],
        sanctioning_authority_user_id=route["sanctioning_authority_user_id"], action_reason=reason,
    )
    _record(child, actor.user_id, "extension_requested", "draft", child.status, reason)
    _notify(child.current_assignee_user_id, child, "task_assigned", "An ELM leave extension needs your action.")
    return child


@transaction.atomic
def create_resumption(actor, parent, actual_date, details=""):
    parent = LeaveApplication.objects.select_for_update().get(pk=parent.pk)
    if parent.applicant_user_id != actor.user_id or parent.status != "approved":
        raise ValidationError({"request": "Only your own approved leave can be resumed."})
    if parent.related_requests.filter(request_type="resumption").exists():
        raise ValidationError({"request": "A resumption review has already been submitted for this leave."})
    if parent.category not in {"EL", "COL", "VL"}:
        raise ValidationError({"category": "Formal resumption review applies to EL, COL, and VL."})
    hierarchy = LeaveHierarchy.objects.filter(unit_key=parent.department, active=True).first()
    if hierarchy is None or not hierarchy.sanctioning_authority_user_id:
        raise ValidationError({"routing": "No sanctioning authority is configured for this unit."})
    if actual_date < parent.start_date:
        raise ValidationError({"actual_resumption_date": "Resumption date cannot precede the original leave start date."})
    assignee = hierarchy.sanctioning_authority_user_id
    app = LeaveApplication.objects.create(
        applicant_user_id=parent.applicant_user_id, employee_kind=parent.employee_kind,
        department=parent.department, request_type="resumption", parent_application=parent,
        category=parent.category, start_date=parent.start_date, end_date=parent.end_date,
        cl_half=parent.cl_half, requested_days=parent.requested_days,
        requested_days_by_year=parent.requested_days_by_year, purpose=parent.purpose,
        status="awaiting_resumption_review", current_assignee_user_id=assignee,
        unit_head_user_id=parent.unit_head_user_id, sanctioning_authority_user_id=assignee,
        actual_resumption_date=actual_date, action_reason=details,
    )
    _record(app, actor.user_id, "resumption_submitted", "draft", app.status, details)
    _notify(assignee, app, "task_assigned", "An ELM resumption review needs your action.")
    return app


def process_year_end(year: int, actor_user_id=None):
    """Run annual lapse/carry-forward/VL-to-EL conversion once per year."""
    with transaction.atomic():
        run, created = LeaveYearEndRun.objects.get_or_create(year=year, defaults={"run_by_user_id": actor_user_id})
        if not created:
            raise ValidationError({"year": f"Year-end processing for {year} has already run."})
        exceptions = []
        accounts = list(LeaveBalance.objects.select_for_update().filter(year=year).order_by("user_id", "category"))
        processed = 0
        for account in accounts:
            available = max(Decimal("0"), account.available)
            policy = LeavePolicy.objects.filter(category=account.category).first()
            if account.category == "VL":
                account.converted_out += available
                account.save(update_fields=["converted_out", "updated_at"])
                converted = (available / Decimal("2")).quantize(Decimal("0.01"))
                if converted:
                    el = _balance(account.user_id, account.employee_kind, year + 1, "EL")
                    el = LeaveBalance.objects.select_for_update().get(pk=el.pk)
                    el.converted_in += converted
                    el.save(update_fields=["converted_in", "updated_at"])
                    LeaveLedgerEntry.objects.get_or_create(reference_key=f"year-end:{year}:{account.user_id}:VL:convert",
                        defaults={"user_id": account.user_id, "employee_kind": account.employee_kind,
                                  "year": year + 1, "category": "EL", "entry_type": "convert_in",
                                  "units": converted, "actor_user_id": actor_user_id,
                                  "note": f"VL conversion at 2:1 from {year}"})
                if available:
                    LeaveLedgerEntry.objects.get_or_create(reference_key=f"year-end:{year}:{account.user_id}:VL:convert-out",
                        defaults={"user_id": account.user_id, "employee_kind": account.employee_kind,
                                  "year": year, "category": "VL", "entry_type": "convert_out",
                                  "units": available, "actor_user_id": actor_user_id,
                                  "note": f"Unused VL converted at year end {year}"})
            elif policy is not None and policy.carry_forward:
                if available:
                    next_account = _balance(account.user_id, account.employee_kind, year + 1, account.category)
                    next_account = LeaveBalance.objects.select_for_update().get(pk=next_account.pk)
                    next_account.carried_in += available
                    next_account.save(update_fields=["carried_in", "updated_at"])
                    LeaveLedgerEntry.objects.get_or_create(
                        reference_key=f"year-end:{year}:{account.user_id}:{account.category}:carry",
                        defaults={
                            "user_id": account.user_id, "employee_kind": account.employee_kind,
                            "year": year + 1, "category": account.category, "entry_type": "carry_forward",
                            "units": available, "actor_user_id": actor_user_id,
                            "note": f"Carry forward from {year}",
                        },
                    )
            else:
                account.lapsed += available
                account.save(update_fields=["lapsed", "updated_at"])
                if available:
                    LeaveLedgerEntry.objects.get_or_create(
                        reference_key=f"year-end:{year}:{account.user_id}:{account.category}:lapse",
                        defaults={
                            "user_id": account.user_id, "employee_kind": account.employee_kind,
                            "year": year, "category": account.category, "entry_type": "lapse",
                            "units": available, "actor_user_id": actor_user_id,
                            "note": f"Unused {account.category} balance lapsed at year end {year}",
                        },
                    )
            processed += 1
        run.processed_accounts = processed
        run.exceptions = exceptions
        run.save(update_fields=["processed_accounts", "exceptions", "updated_at"])
        return run


def process_sla_thresholds(now=None):
    """Process configured pending-task reminders/escalations; safe to run repeatedly."""
    now = now or timezone.now()
    config = LeaveSLAConfig.objects.order_by("id").first()
    if not config:
        config = LeaveSLAConfig.objects.create()
    pending = LeaveApplication.objects.filter(status__in=PENDING_STATUSES,
                                               current_assignee_user_id__isnull=False,
                                               created_at__lte=now - timedelta(hours=config.reminder_after_hours))
    events_created = 0
    for app in pending.iterator():
        _, reminder_created = LeaveSLAEvent.objects.get_or_create(
            application=app, event_type="reminder",
            defaults={"note": "Pending at reminder threshold"},
        )
        if reminder_created:
            _notify(app.current_assignee_user_id, app, "sla_reminder", "An ELM task is still pending; please review it.")
            events_created += 1
        if app.created_at <= now - timedelta(hours=config.escalation_after_hours):
            _, escalation_created = LeaveSLAEvent.objects.get_or_create(
                application=app, event_type="escalation",
                defaults={"note": "Pending past escalation threshold"},
            )
            if escalation_created:
                _notify(config.escalation_user_id or app.current_assignee_user_id, app, "sla_escalation", "An ELM task has crossed its escalation threshold.")
                events_created += 1
    return events_created
