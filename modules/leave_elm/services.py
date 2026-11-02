from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.leave_elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveBalance,
    LeaveDecision,
    LeaveHierarchy,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveResumption,
    LeaveSLAConfig,
    LeaveSLAEvent,
    LeaveYearEndConfig,
    LeaveYearEndRun,
    VacationPeriod,
)
from modules.placement.services import notifications

ZERO = Decimal("0")
P_APPLY = "leave_elm.apply.self"
P_VIEW_SELF = "leave_elm.view.self"
P_REVIEW_UNIT = "leave_elm.review.unit"
P_REVIEW_ESTABLISHMENT = "leave_elm.review.establishment"
P_REVIEW_FINAL = "leave_elm.review.final"
P_MANAGE_RECORDS = "leave_elm.manage.records"
P_PROCESS_SLA = "leave_elm.process.sla"


def has_permission(actor, code: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check and check(code))


def require_permission(actor, code: str) -> None:
    if actor is None or not has_permission(actor, code):
        raise PermissionDeniedError(
            "You do not have permission to perform this leave action.",
            code="permission_denied",
        )


def is_employee_kind(kind: str) -> bool:
    return kind in {"faculty", "staff"}


def _employee(actor):
    if actor is None or not is_employee_kind(getattr(actor, "kind", "")):
        raise PermissionDeniedError(
            "Only Faculty and Staff may use employee leave functions.",
            code="employee_role_required",
        )
    require_permission(actor, P_APPLY)
    person = directory.get_users([actor.user_id]).get(actor.user_id)
    if person is None:
        raise ConflictError(
            "Your employee record is not available in the Fusion directory.",
            code="employee_record_missing",
        )
    return person


def _current_holidays(years: set[int]):
    effective_ids = [
        HolidayCalendar.objects.filter(year=year, is_published=True)
        .order_by("-published_at", "-pk").values_list("pk", flat=True).first()
        for year in years
    ]
    return set(HolidayDate.objects.filter(
        calendar_id__in=[calendar_id for calendar_id in effective_ids if calendar_id],
        is_closed=True,
    ).values_list("date", flat=True))


def _days_by_year(category: str, start: date, end: date, half_day_period="full"):
    if category == "CL" and half_day_period != "full":
        return {start.year: Decimal("0.5")}
    if category == "RH":
        return {start.year: Decimal("1")}
    days = {}
    for year in range(start.year, end.year + 1):
        first = max(start, date(year, 1, 1))
        last = min(end, date(year, 12, 31))
        if category in {"EL", "COL", "VL"}:
            days[year] = Decimal((last - first).days + 1)
            continue
        closed_dates = _current_holidays({year})
        days[year] = Decimal(sum(
            1 for offset in range((last - first).days + 1)
            if (day := first + timedelta(days=offset)).weekday() < 5
            and day not in closed_dates
        ))
    return days


def _days(category: str, start: date, end: date, half_day_period="full") -> Decimal:
    return sum(
        _days_by_year(category, start, end, half_day_period).values(), ZERO,
    )


def _policy(category: str, employee_kind: str) -> LeavePolicy:
    try:
        policy = LeavePolicy.objects.get(category=category)
    except LeavePolicy.DoesNotExist as exc:
        raise ConflictError(
            f"No current policy is configured for {category}.",
            code="leave_policy_missing",
        ) from exc
    if not getattr(policy, f"{employee_kind}_eligible"):
        raise ConflictError(
            f"{category} is not available to {employee_kind} employees.",
            code="leave_category_not_applicable",
        )
    return policy


def _ledger(balance, entry_type, amount, reference, note="", actor_user_id=None):
    return LeaveLedgerEntry.objects.create(
        balance=balance,
        entry_type=entry_type,
        amount=amount,
        reference=reference,
        note=note,
        actor_user_id=actor_user_id,
    )


def get_balance(employee_id: int, employee_kind: str, category: str, year: int):
    policy = _policy(category, employee_kind)
    balance = LeaveBalance.objects.filter(
        employee_id=employee_id, category=category, year=year,
    ).first()
    if balance:
        return balance

    entitlement = policy.entitlement_for(employee_kind)
    with transaction.atomic():
        balance, created = LeaveBalance.objects.get_or_create(
            employee_id=employee_id,
            category=category,
            year=year,
            defaults={
                "employee_kind": employee_kind,
                "entitlement": entitlement,
                "remaining": entitlement,
            },
        )
        if created and entitlement:
            _ledger(
                balance, "credit", entitlement,
                f"annual:{employee_id}:{category}:{year}",
                "Annual entitlement",
            )
        if created and policy.carry_forward and year > 1:
            previous = LeaveBalance.objects.filter(
                employee_id=employee_id, category=category, year=year - 1,
            ).first()
            if previous and previous.remaining:
                carry = previous.remaining
                if policy.carry_forward_cap is not None:
                    carry = min(carry, policy.carry_forward_cap)
                balance.carried_in = carry
                balance.remaining += carry
                balance.save(update_fields=("carried_in", "remaining", "updated_at"))
                _ledger(
                    balance, "carry", carry,
                    f"carry:{employee_id}:{category}:{year}",
                    f"Carry-forward from {year - 1}",
                )
        return balance


def available_balance(balance):
    year_start = date(balance.year, 1, 1)
    year_end = date(balance.year, 12, 31)
    reserved = ZERO
    for application in LeaveApplication.objects.filter(
        employee_id=balance.employee_id,
        category=balance.category,
        status__in=(
            "substitute_response", "unit_head_review",
            "establishment_review", "final_review",
        ),
        request_type__in=("leave", "extension"),
        start_date__lte=year_end,
        end_date__gte=year_start,
    ):
        reserved += _days(
            application.category,
            max(application.start_date, year_start),
            min(application.end_date, year_end),
            application.half_day_period,
        )
    return balance.remaining - reserved


def _validate_dates(category: str, start: date, end: date, policy: LeavePolicy):
    if end < start:
        raise ConflictError("The end date must not precede the start date.",
                            code="invalid_date_range")
    if category == "RH":
        if start != end:
            raise ConflictError("An RH request must be for one restricted holiday.",
                                code="invalid_rh_period")
        effective_calendar_id = (
            HolidayCalendar.objects.filter(year=start.year, is_published=True)
            .order_by("-published_at", "-pk").values_list("pk", flat=True).first()
        )
        if not effective_calendar_id or not HolidayDate.objects.filter(
            date=start, is_restricted=True, calendar_id=effective_calendar_id,
        ).exists():
            raise ConflictError(
                "The selected date is not a published Restricted Holiday.",
                code="not_restricted_holiday",
            )
    if policy.vacation_period_required and not VacationPeriod.objects.filter(
        year=start.year, start_date__lte=start, end_date__gte=end,
    ).exists():
        raise ConflictError(
            "VL must fall entirely within a supplied vacation period.",
            code="outside_vacation_period",
        )


def _overlap(employee_id, category, start, end, half_day_period, *, exclude_id=None,
             exclude_parent_id=None):
    active = LeaveApplication.objects.filter(
        employee_id=employee_id,
        status__in=(
            "substitute_response", "unit_head_review", "establishment_review",
            "final_review", "approved",
        ),
        start_date__lte=end,
        end_date__gte=start,
        request_type__in=("leave", "extension", "offline"),
    )
    if exclude_id:
        active = active.exclude(pk=exclude_id)
    if exclude_parent_id:
        active = active.exclude(pk=exclude_parent_id)
    for existing in active:
        existing_end = existing.actual_end_date or existing.end_date
        if existing.start_date > end or existing_end < start:
            continue
        same_half_day = (
            category == existing.category == "CL"
            and start == end == existing.start_date == existing.end_date
            and half_day_period != "full"
            and existing.half_day_period != "full"
            and half_day_period != existing.half_day_period
        )
        if not same_half_day:
            raise ConflictError(
                "The requested dates overlap another pending or approved leave.",
                code="leave_overlap",
            )


def _check_balance(employee_id, employee_kind, category, start, end, half_day_period,
                   *, exclude_parent_id=None):
    pending_base = LeaveApplication.objects.filter(
        employee_id=employee_id,
        category=category,
        status__in=(
            "substitute_response", "unit_head_review", "establishment_review",
            "final_review",
        ),
        request_type__in=("leave", "extension"),
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude_parent_id:
        pending_base = pending_base.exclude(parent_application_id=exclude_parent_id)
    for year, requested in _days_by_year(
        category, start, end, half_day_period,
    ).items():
        balance = get_balance(employee_id, employee_kind, category, year)
        year_start, year_end = date(year, 1, 1), date(year, 12, 31)
        reserved = ZERO
        for row in pending_base.filter(
            start_date__lte=year_end, end_date__gte=year_start,
        ):
            reserved += _days(
                row.category,
                max(row.start_date, year_start),
                min(row.end_date, year_end),
                row.half_day_period,
            )
        if requested > balance.remaining - reserved:
            raise ConflictError(
                f"Insufficient {category} balance in {year}: "
                f"{balance.remaining - reserved} available.",
                code="insufficient_leave_balance",
            )
    return requested


def _validate_substitute(employee_id, substitute_id, start, end):
    if substitute_id is None:
        return
    if substitute_id == employee_id:
        raise ConflictError("The applicant cannot be their own substitute.",
                            code="invalid_substitute")
    substitute = directory.get_users([substitute_id]).get(substitute_id)
    if substitute is None or not is_employee_kind(substitute.kind):
        raise ConflictError("The substitute must be another Fusion employee.",
                            code="invalid_substitute")
    if LeaveApplication.objects.filter(
        employee_id=substitute_id,
        status__in=("substitute_response", "unit_head_review",
                    "establishment_review", "final_review", "approved"),
        request_type__in=("leave", "extension", "offline"),
        start_date__lte=end, end_date__gte=start,
    ).exists():
        raise ConflictError(
            "The nominated substitute has overlapping pending or approved leave.",
            code="substitute_unavailable",
        )


def _hierarchy(department: str, category: str) -> LeaveHierarchy:
    hierarchy = LeaveHierarchy.objects.filter(
        department=department, category=category,
    ).first()
    if hierarchy is None:
        raise ConflictError(
            "Leave routing is not configured for this department and category.",
            code="leave_hierarchy_missing",
        )
    if category not in {"CL", "RH"} and not hierarchy.final_authority_user_id:
        raise ConflictError(
            "The final sanctioning authority is not configured.",
            code="leave_authority_missing",
        )
    return hierarchy


def _validate_hierarchy_for_employee(hierarchy, category, employee_id):
    if hierarchy.unit_head_user_id == employee_id:
        raise ConflictError(
            "The applicant cannot be the Unit Head reviewing their own request.",
            code="invalid_leave_hierarchy",
        )
    if (category not in {"CL", "RH"}
            and hierarchy.final_authority_user_id == employee_id):
        raise ConflictError(
            "Only the Director self-sanction path may assign an applicant as final authority.",
            code="invalid_leave_hierarchy",
        )


def _notify(user_id, topic, key, subject, body):
    if user_id:
        notifications.enqueue(
            topic=topic,
            dedupe_key=key,
            recipient_user_id=user_id,
            subject=subject,
            body=body,
            payload={"module": "leave_elm"},
        )


def _assign(application, status, user_id, role):
    application.status = status
    application.assigned_user_id = user_id
    application.assigned_role = role
    application.assigned_at = timezone.now()
    application.reminder_sent_at = None
    application.escalation_sent_at = None
    application.save()
    _notify(
        user_id, "leave.task.assigned",
        f"leave:{application.pk}:{status}:{user_id}",
        "Leave request requires action",
        f"Leave request {application.pk} is awaiting {role} action.",
    )


def _route_to_unit_head(application, hierarchy):
    _assign(application, "unit_head_review", hierarchy.unit_head_user_id, "unit_head")


def apply_leave(actor, data):
    person = _employee(actor)
    category = data["category"]
    policy = _policy(category, person.kind)
    start, end = data["start_date"], data["end_date"]
    period = data.get("half_day_period", "full")
    if period != "full" and (category != "CL" or start != end):
        raise ConflictError(
            "Only a single-day CL request can be half-day.",
            code="invalid_half_day",
        )
    if period not in {"full", "first_half", "second_half"}:
        raise ConflictError("Invalid CL half-day selection.", code="invalid_half_day")
    if policy.substitute_required and data.get("substitute_user_id") is None:
        raise ConflictError("This request requires a substitute.",
                            code="substitute_required")
    if policy.evidence_required and not data.get("evidence_reference", "").strip():
        raise ConflictError("Supporting evidence is required.", code="evidence_required")
    if data.get("station_leave") and not data.get("station_destination", "").strip():
        raise ConflictError("Station Leave requires a destination.",
                            code="station_destination_required")

    department = person.department
    is_director = "director" in {str(role).casefold() for role in actor.roles}
    hierarchy = None if is_director else _hierarchy(department, category)
    if hierarchy:
        _validate_hierarchy_for_employee(hierarchy, category, actor.user_id)
    if not is_director:
        _validate_dates(category, start, end, policy)
        _overlap(actor.user_id, category, start, end, period)
        _validate_substitute(
            actor.user_id, data.get("substitute_user_id"), start, end,
        )
        _check_balance(
            actor.user_id, person.kind, category, start, end, period,
        )
    else:
        _validate_dates(category, start, end, policy)
        _overlap(actor.user_id, category, start, end, period)
        _validate_substitute(actor.user_id, data.get("substitute_user_id"), start, end)
        _check_balance(actor.user_id, person.kind, category, start, end, period)

    with transaction.atomic():
        application = LeaveApplication.objects.create(
            employee_id=actor.user_id,
            employee_kind=person.kind,
            department=department,
            category=category,
            start_date=start,
            end_date=end,
            half_day_period=period,
            reason=data["reason"],
            station_leave=data.get("station_leave", False),
            station_destination=data.get("station_destination", ""),
            station_contact=data.get("station_contact", ""),
            evidence_reference=data.get("evidence_reference", ""),
            substitute_user_id=data.get("substitute_user_id"),
        )
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id, action="submitted",
        )
        if is_director:
            _assign(application, "final_review", actor.user_id, "director")
        elif application.substitute_user_id:
            _assign(
                application, "substitute_response",
                application.substitute_user_id, "substitute",
            )
        else:
            _route_to_unit_head(application, hierarchy)
    return application


def _owned_application(actor, application_id, *, allow_staff=False):
    query = LeaveApplication.objects.filter(pk=application_id)
    if allow_staff and has_permission(actor, "leave_elm.view.all"):
        application = query.first()
    else:
        application = query.filter(employee_id=getattr(actor, "user_id", None)).first()
    if application is None:
        raise NotFoundError("Leave request not found.")
    return application


def _effective_end(application):
    if application.actual_end_date:
        return application.actual_end_date
    extension_end = application.related_requests.filter(
        request_type="extension", status="approved",
    ).aggregate(value=Max("end_date"))["value"]
    return max(application.end_date, extension_end) if extension_end else application.end_date


def withdraw(actor, application_id):
    require_permission(actor, P_VIEW_SELF)
    with transaction.atomic():
        application = _owned_application(actor, application_id)
        if not application.is_pending:
            raise ConflictError("Only a pending request can be withdrawn.",
                                code="request_not_pending")
        previous_assignee = application.assigned_user_id
        application.status = "withdrawn"
        application.assigned_user_id = None
        application.assigned_role = ""
        application.save()
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id, action="withdrawn",
        )
        _notify(
            previous_assignee, "leave.status.changed",
            f"leave:{application.pk}:withdrawn:assignee:{previous_assignee}",
            "Leave request withdrawn",
            f"Leave request {application.pk} was withdrawn by the employee.",
        )
        _notify(
            application.employee_id, "leave.status.changed",
            f"leave:{application.pk}:withdrawn",
            "Leave request withdrawn", f"Leave request {application.pk} was withdrawn.",
        )
    return application


def _post_debit(application, actor_user_id=None):
    amounts = _days_by_year(
        application.category, application.start_date,
        application.end_date, application.half_day_period,
    )
    balances = {
        year: LeaveBalance.objects.select_for_update().get(
            employee_id=application.employee_id,
            category=application.category,
            year=year,
        )
        for year in amounts
    }
    if any(amount > balances[year].remaining for year, amount in amounts.items()):
        raise ConflictError("The available balance changed before approval.",
                            code="insufficient_leave_balance")
    for year, amount in amounts.items():
        balance = balances[year]
        balance.remaining -= amount
        balance.used += amount
        balance.save(update_fields=("remaining", "used", "updated_at"))
        _ledger(
            balance, "debit", -amount, f"leave-debit:{application.pk}:{year}",
            f"Approved {application.request_type}", actor_user_id,
        )


def _restore_debit(application, actor_user_id):
    reference = f"leave-restore:{application.pk}"
    if LeaveLedgerEntry.objects.filter(reference=reference).exists():
        return
    amounts = _days_by_year(
        application.category, application.start_date,
        application.end_date, application.half_day_period,
    )
    for year, amount in amounts.items():
        balance = LeaveBalance.objects.select_for_update().get(
            employee_id=application.employee_id,
            category=application.category,
            year=year,
        )
        balance.remaining += amount
        balance.used -= amount
        balance.save(update_fields=("remaining", "used", "updated_at"))
        _ledger(
            balance, "restore", amount, f"{reference}:{year}",
            "Approved leave cancelled", actor_user_id,
        )


def _finish(application, actor, decision, note=""):
    if decision not in {"approve", "reject"}:
        raise ConflictError("Decision must be approve or reject.",
                            code="invalid_decision")
    if application.assigned_user_id != actor.user_id:
        raise PermissionDeniedError("This request is not assigned to you.",
                                    code="not_assigned")
    if application.status == "unit_head_review":
        require_permission(actor, P_REVIEW_UNIT)
        if application.category not in {"CL", "RH"}:
            recommendation = "recommended" if decision == "approve" else "not_recommended"
            application.unit_head_recommendation = recommendation
            hierarchy = _hierarchy(application.department, application.category)
            if hierarchy.establishment_user_id:
                _assign(application, "establishment_review",
                        hierarchy.establishment_user_id, "establishment")
            else:
                _assign(application, "final_review",
                        hierarchy.final_authority_user_id, "final_authority")
            application.unit_head_recommendation = recommendation
            application.save(update_fields=("unit_head_recommendation",))
            LeaveDecision.objects.create(
                application=application,
                actor_user_id=actor.user_id,
                action=recommendation,
                note=note,
            )
            return application
    elif application.status == "establishment_review":
        require_permission(actor, P_REVIEW_ESTABLISHMENT)
        hierarchy = _hierarchy(application.department, application.category)
        _assign(
            application, "final_review",
            hierarchy.final_authority_user_id, "final_authority",
        )
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id,
            action="routed", note=note,
        )
        return application
    elif application.status == "final_review":
        require_permission(actor, P_REVIEW_FINAL)
    else:
        raise ConflictError("This request is not awaiting your decision.",
                            code="request_not_pending")

    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(pk=application.pk)
        if not application.is_pending:
            raise ConflictError("This request has already been processed.",
                                code="request_not_pending")
        was_cancellation = application.request_type == "cancellation"
        was_extension = application.request_type == "extension"
        if decision == "approve":
            if was_cancellation:
                parent = LeaveApplication.objects.select_for_update().get(
                    pk=application.parent_application_id,
                )
                parent.status = "cancelled"
                parent.save(update_fields=("status", "updated_at"))
                _restore_debit(parent, actor.user_id)
            elif was_extension:
                _post_debit(application, actor.user_id)
            else:
                _post_debit(application, actor.user_id)
            application.status = "approved"
        else:
            application.status = "rejected"
        application.final_decision_by = actor.user_id
        application.final_decision_at = timezone.now()
        application.decision_note = note
        application.assigned_user_id = None
        application.assigned_role = ""
        application.save()
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id,
            action=decision, note=note,
        )
        _notify(
            application.employee_id, "leave.status.changed",
            f"leave:{application.pk}:final:{decision}",
            f"Leave request {decision}d",
            f"Leave request {application.pk} was {decision}d.",
        )
    return application


def decide(actor, application_id, decision, note=""):
    application = LeaveApplication.objects.filter(
        pk=application_id,
        assigned_user_id=getattr(actor, "user_id", None),
        status__in=("unit_head_review", "establishment_review", "final_review"),
    ).first()
    if application is None:
        raise NotFoundError("Assigned leave task not found.")
    return _finish(application, actor, decision, note)


def respond_substitute(actor, application_id, accept: bool):
    application = LeaveApplication.objects.filter(
        pk=application_id, status="substitute_response",
        assigned_user_id=getattr(actor, "user_id", None),
    ).first()
    if application is None:
        raise NotFoundError("Substitute request not found.")
    require_permission(actor, "leave_elm.substitute.respond")
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(pk=application.pk)
        application.substitute_accepted = accept
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id,
            action="substitute_accepted" if accept else "substitute_declined",
        )
        if accept:
            hierarchy = _hierarchy(application.department, application.category)
            _route_to_unit_head(application, hierarchy)
        else:
            application.assigned_user_id = application.employee_id
            application.assigned_role = "employee"
            application.assigned_at = timezone.now()
            application.save()
            _notify(
                application.employee_id, "leave.status.changed",
                f"leave:{application.pk}:substitute-declined:{actor.user_id}",
                "Substitute declined",
                f"Request {application.pk}: the substitute declined; "
                "nominate a replacement or withdraw.",
            )
        return application


def replace_substitute(actor, application_id, substitute_user_id):
    require_permission(actor, P_APPLY)
    application = _owned_application(actor, application_id)
    if application.status != "substitute_response" or application.substitute_accepted is not False:
        raise ConflictError("A replacement is available only after a decline.",
                            code="substitute_replacement_unavailable")
    _validate_substitute(
        actor.user_id, substitute_user_id, application.start_date, application.end_date,
    )
    application.substitute_user_id = substitute_user_id
    application.substitute_accepted = None
    _assign(application, "substitute_response", substitute_user_id, "substitute")
    LeaveDecision.objects.create(
        application=application, actor_user_id=actor.user_id,
        action="substitute_replaced",
    )
    return application


def request_cancellation(actor, application_id):
    require_permission(actor, "leave_elm.cancel.self")
    parent = _owned_application(actor, application_id)
    if parent.status != "approved" or parent.start_date <= timezone.localdate():
        raise ConflictError(
            "Cancellation is available only before approved leave begins.",
            code="cancellation_window_closed",
        )
    if parent.related_requests.filter(
        request_type="cancellation",
        status__in=("unit_head_review", "establishment_review", "final_review"),
    ).exists():
        raise ConflictError("A cancellation request is already pending.",
                            code="cancellation_already_pending")
    hierarchy = _hierarchy(parent.department, parent.category)
    _validate_hierarchy_for_employee(hierarchy, parent.category, actor.user_id)
    with transaction.atomic():
        request = LeaveApplication.objects.create(
            employee_id=parent.employee_id,
            employee_kind=parent.employee_kind,
            department=parent.department,
            category=parent.category,
            request_type="cancellation",
            start_date=parent.start_date,
            end_date=parent.end_date,
            reason="Cancellation requested by employee",
            parent_application=parent,
        )
        _route_to_unit_head(request, hierarchy)
        LeaveDecision.objects.create(
            application=request, actor_user_id=actor.user_id,
            action="cancellation_requested",
        )
    return request


def request_extension(actor, application_id, data):
    require_permission(actor, "leave_elm.extend.self")
    parent = _owned_application(actor, application_id)
    today = timezone.localdate()
    effective_end = _effective_end(parent)
    if (parent.status != "approved" or parent.category not in {"EL", "COL", "VL"}
            or parent.actual_end_date is not None
            or not parent.start_date <= today <= effective_end):
        raise ConflictError("Only ongoing EL, COL, or VL can be extended.",
                            code="extension_not_applicable")
    start = effective_end + timedelta(days=1)
    new_end_date = data["new_end_date"]
    if new_end_date < start:
        raise ConflictError("Extension must add at least one day.",
                            code="invalid_extension_period")
    policy = _policy(parent.category, parent.employee_kind)
    if policy.substitute_required and data.get("substitute_user_id") is None:
        raise ConflictError("This extension requires a substitute.",
                            code="substitute_required")
    if policy.evidence_required and not data.get("evidence_reference", "").strip():
        raise ConflictError("Supporting evidence is required.", code="evidence_required")
    if data.get("station_leave") and not data.get("station_destination", "").strip():
        raise ConflictError("Station Leave requires a destination.",
                            code="station_destination_required")
    _validate_dates(parent.category, start, new_end_date, policy)
    _overlap(
        parent.employee_id, parent.category, start, new_end_date, "full",
        exclude_parent_id=parent.pk,
    )
    _check_balance(
        parent.employee_id, parent.employee_kind, parent.category,
        start, new_end_date, "full", exclude_parent_id=parent.pk,
    )
    _validate_substitute(
        parent.employee_id, data.get("substitute_user_id"), start, new_end_date,
    )
    hierarchy = _hierarchy(parent.department, parent.category)
    _validate_hierarchy_for_employee(hierarchy, parent.category, actor.user_id)
    with transaction.atomic():
        extension = LeaveApplication.objects.create(
            employee_id=parent.employee_id,
            employee_kind=parent.employee_kind,
            department=parent.department,
            category=parent.category,
            request_type="extension",
            start_date=start,
            end_date=new_end_date,
            reason=data["reason"],
            evidence_reference=data.get("evidence_reference", ""),
            substitute_user_id=data.get("substitute_user_id"),
            station_leave=data.get("station_leave", False),
            station_destination=data.get("station_destination", ""),
            station_contact=data.get("station_contact", ""),
            parent_application=parent,
        )
        if extension.substitute_user_id:
            _assign(
                extension, "substitute_response",
                extension.substitute_user_id, "substitute",
            )
        else:
            _route_to_unit_head(extension, hierarchy)
        LeaveDecision.objects.create(
            application=extension, actor_user_id=actor.user_id,
            action="extension_requested",
        )
    return extension


def submit_resumption(actor, application_id, actual_date, details):
    require_permission(actor, "leave_elm.resume.self")
    application = _owned_application(actor, application_id)
    if application.category not in {"EL", "COL", "VL"} or application.status != "approved":
        raise ConflictError("Resumption applies only to approved EL, COL, or VL.",
                            code="resumption_not_applicable")
    if actual_date < application.start_date:
        raise ConflictError("Resumption date cannot precede leave start.",
                            code="invalid_resumption_date")
    if actual_date > timezone.localdate():
        raise ConflictError("Resumption can be submitted after the actual return date.",
                            code="resumption_not_yet_due")
    if LeaveResumption.objects.filter(application=application).exists():
        raise ConflictError("A resumption has already been submitted.",
                            code="resumption_already_submitted")
    hierarchy = _hierarchy(application.department, application.category)
    reviewer_id = hierarchy.final_authority_user_id or hierarchy.unit_head_user_id
    with transaction.atomic():
        resumption = LeaveResumption.objects.create(
            application=application,
            actual_resume_date=actual_date,
            details=details,
            assigned_user_id=reviewer_id,
        )
        _notify(
            reviewer_id, "leave.task.assigned",
            f"leave:resumption:{resumption.pk}:assigned:{reviewer_id}",
            "Leave resumption requires review",
            f"Resumption request {resumption.pk} is awaiting authority review.",
        )
        return resumption


def review_resumption(actor, resumption_id, decision, note=""):
    resumption = LeaveResumption.objects.select_related("application").filter(
        pk=resumption_id, assigned_user_id=getattr(actor, "user_id", None),
        status="pending",
    ).first()
    if resumption is None:
        raise NotFoundError("Resumption request not found.")
    require_permission(actor, P_REVIEW_FINAL)
    with transaction.atomic():
        resumption = LeaveResumption.objects.select_for_update().select_related(
            "application",
        ).get(pk=resumption.pk)
        if decision not in {"approve", "reject"}:
            raise ConflictError("Decision must be approve or reject.",
                                code="invalid_decision")
        resumption.status = "approved" if decision == "approve" else "rejected"
        resumption.reviewed_by_user_id = actor.user_id
        resumption.reviewed_at = timezone.now()
        resumption.review_note = note
        resumption.save()
        if decision == "approve":
            application = resumption.application
            approved_end = _effective_end(application)
            actual_end = resumption.actual_resume_date
            application.actual_end_date = actual_end
            application.save(update_fields=("actual_end_date", "updated_at"))
            if approved_end > actual_end:
                delta_start, delta_end, factor = actual_end + timedelta(days=1), approved_end, 1
            elif actual_end > approved_end:
                delta_start, delta_end, factor = approved_end + timedelta(days=1), actual_end, -1
            else:
                delta_start, delta_end, factor = None, None, 0
            if factor:
                for year, amount in _days_by_year(
                    application.category, delta_start, delta_end,
                ).items():
                    balance = LeaveBalance.objects.select_for_update().get(
                        employee_id=application.employee_id,
                        category=application.category,
                        year=year,
                    )
                    ledger_amount = amount * factor
                    if factor < 0 and amount > balance.remaining:
                        raise ConflictError(
                            "Late resumption exceeds the available leave balance.",
                            code="insufficient_leave_balance",
                        )
                    balance.remaining += ledger_amount
                    balance.used -= ledger_amount
                    entry_type = "adjustment"
                    balance.save(update_fields=("remaining", "used", "updated_at"))
                    _ledger(
                        balance, entry_type, ledger_amount,
                        f"resumption:{resumption.pk}:{year}",
                        "Actual resumption adjustment", actor.user_id,
                    )
        return resumption


def record_offline_leave(actor, data):
    require_permission(actor, P_MANAGE_RECORDS)
    if not data.get("evidence_reference", "").strip():
        raise ConflictError("Sanction/reference evidence is required.",
                            code="evidence_required")
    person = directory.get_users([data["employee_id"]]).get(data["employee_id"])
    if person is None or not is_employee_kind(person.kind):
        raise ConflictError("The employee is not in the Fusion directory.",
                            code="employee_record_missing")
    category = data["category"]
    policy = _policy(category, person.kind)
    _validate_dates(category, data["start_date"], data["end_date"], policy)
    if policy.evidence_required and not data.get("evidence_reference", "").strip():
        raise ConflictError("Supporting evidence is required.", code="evidence_required")
    _overlap(data["employee_id"], category, data["start_date"], data["end_date"], "full")
    _check_balance(
        data["employee_id"], person.kind, category,
        data["start_date"], data["end_date"], "full",
    )
    with transaction.atomic():
        application = LeaveApplication.objects.create(
            employee_id=data["employee_id"],
            employee_kind=person.kind,
            department=person.department,
            category=category,
            request_type="offline",
            status="approved",
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            evidence_reference=data["evidence_reference"],
            final_decision_by=actor.user_id,
            final_decision_at=timezone.now(),
        )
        _post_debit(application, actor.user_id)
        LeaveDecision.objects.create(
            application=application, actor_user_id=actor.user_id,
            action="offline_synchronized", note=data["evidence_reference"],
        )
    return application


def process_year_end(year: int):
    """Apply the configured entitlement rules to every locally projected employee."""
    completed = 0
    for person in directory.get_employees():
        with transaction.atomic():
            _, created = LeaveYearEndRun.objects.get_or_create(
                employee_id=person.user_id, year=year,
            )
            if not created:
                continue
            previous = {}
            policies = {}
            for category, _ in LeavePolicy.CATEGORIES:
                policy = LeavePolicy.objects.get(category=category)
                if not getattr(policy, f"{person.kind}_eligible"):
                    continue
                policies[category] = policy
                old = LeaveBalance.objects.filter(
                    employee_id=person.user_id, category=category, year=year - 1,
                ).first()
                previous[category] = old
                if old is None:
                    get_balance(person.user_id, person.kind, category, year - 1)
                    previous[category] = LeaveBalance.objects.get(
                        employee_id=person.user_id, category=category, year=year - 1,
                    )

            next_balances = {}
            for category, _ in LeavePolicy.CATEGORIES:
                policy = policies.get(category)
                if policy is None:
                    continue
                new_balance, _ = LeaveBalance.objects.get_or_create(
                    employee_id=person.user_id,
                    category=category,
                    year=year,
                    defaults={
                        "employee_kind": person.kind,
                        "entitlement": policy.entitlement_for(person.kind),
                        "remaining": policy.entitlement_for(person.kind),
                    },
                )
                if not LeaveLedgerEntry.objects.filter(
                    reference=f"annual:{person.user_id}:{category}:{year}",
                ).exists() and new_balance.entitlement:
                    _ledger(
                        new_balance, "credit", new_balance.entitlement,
                        f"annual:{person.user_id}:{category}:{year}",
                        "Annual entitlement",
                    )
                next_balances[category] = new_balance

            for category, _ in LeavePolicy.CATEGORIES:
                if category not in policies:
                    continue
                old = previous[category]
                if old is None or old.remaining == 0:
                    continue
                remainder = old.remaining
                if category in {"EL", "COL"}:
                    policy = _policy(category, person.kind)
                    carry = remainder if policy.carry_forward else ZERO
                    if carry and policy.carry_forward_cap is not None:
                        carry = min(carry, policy.carry_forward_cap)
                    new_balance = next_balances[category]
                    if new_balance.carried_in == 0 and carry:
                        new_balance.carried_in = carry
                        new_balance.remaining += carry
                        new_balance.save(update_fields=(
                            "carried_in", "remaining", "updated_at",
                        ))
                        _ledger(
                            new_balance, "carry", carry,
                            f"carry:{person.user_id}:{category}:{year}",
                            f"Carry-forward from {year - 1}",
                        )
                    lapse = remainder - carry
                    if lapse:
                        _ledger(
                            old, "lapse", -lapse,
                            f"year-lapse:{person.user_id}:{category}:{year}",
                            "Amount above configured carry-forward cap",
                        )
                elif category == "VL" and person.kind == "faculty":
                    conversion = remainder / Decimal("2")
                    target = next_balances["EL"]
                    target.converted_in += conversion
                    target.remaining += conversion
                    target.save(update_fields=(
                        "converted_in", "remaining", "updated_at",
                    ))
                    _ledger(
                        target, "conversion", conversion,
                        f"vl-to-el:{person.user_id}:{year}",
                        f"Conversion from {remainder} unused VL at 2:1",
                    )
                    _ledger(
                        old, "conversion", -remainder,
                        f"vl-expended:{person.user_id}:{year}",
                        "Unused VL converted to EL",
                    )
                else:
                    _ledger(
                        old, "lapse", -remainder,
                        f"year-lapse:{person.user_id}:{category}:{year}",
                        "Unused leave lapsed at year end",
                    )
                old.remaining = ZERO
                old.save(update_fields=("remaining", "updated_at"))
            completed += 1
    return completed


def process_configured_year_end(on_date=None):
    on_date = on_date or timezone.localdate()
    config = LeaveYearEndConfig.objects.first()
    if config is None or config.month is None or config.day is None:
        raise ConflictError(
            "The year-end boundary has not been configured.",
            code="year_end_boundary_missing",
        )
    if (on_date.month, on_date.day) != (config.month, config.day):
        return {"due": False, "processed_employees": 0}
    return {
        "due": True,
        "processed_employees": process_year_end(on_date.year + 1),
    }


def process_sla_thresholds(now=None):
    now = now or timezone.now()
    reminders = escalations = 0
    tasks = LeaveApplication.objects.filter(
        status__in=(
            "substitute_response", "unit_head_review", "establishment_review",
            "final_review",
        ),
        assigned_user_id__isnull=False,
        assigned_at__isnull=False,
    ).select_related()
    for application in tasks:
        config = LeaveSLAConfig.objects.filter(
            request_type=application.request_type,
        ).first()
        if config is None:
            continue
        elapsed = now - application.assigned_at
        stage = f"{application.status}:{application.assigned_user_id}"
        if (config.reminder_after_hours is not None
                and elapsed >= timedelta(hours=config.reminder_after_hours)
                and application.reminder_sent_at is None):
            with transaction.atomic():
                locked = LeaveApplication.objects.select_for_update().get(pk=application.pk)
                if locked.is_pending and locked.reminder_sent_at is None:
                    LeaveSLAEvent.objects.create(
                        application=locked, event_type="reminder", stage_key=stage,
                    )
                    locked.reminder_sent_at = now
                    locked.save(update_fields=("reminder_sent_at", "updated_at"))
                    _notify(
                        locked.assigned_user_id, "leave.sla.reminder",
                        f"leave:{locked.pk}:reminder:{stage}",
                        "Leave request reminder",
                        f"Leave request {locked.pk} is still awaiting your action.",
                    )
                    reminders += 1
        if (config.escalation_after_hours is not None
                and elapsed >= timedelta(hours=config.escalation_after_hours)
                and application.escalation_sent_at is None):
            with transaction.atomic():
                locked = LeaveApplication.objects.select_for_update().get(pk=application.pk)
                if locked.is_pending and locked.escalation_sent_at is None:
                    recipient = config.escalation_user_id or locked.assigned_user_id
                    LeaveSLAEvent.objects.create(
                        application=locked, event_type="escalation", stage_key=stage,
                    )
                    if config.changes_assignment and config.escalation_user_id:
                        locked.assigned_user_id = config.escalation_user_id
                        locked.assigned_role = "escalated_authority"
                        locked.assigned_at = now
                        locked.reminder_sent_at = None
                    locked.escalation_sent_at = now
                    locked.save()
                    _notify(
                        recipient, "leave.sla.escalated",
                        f"leave:{locked.pk}:escalation:{stage}",
                        "Leave request escalation",
                        f"Leave request {locked.pk} has passed its configured SLA.",
                    )
                    escalations += 1
    for resumption in LeaveResumption.objects.filter(
        status="pending", assigned_user_id__isnull=False,
    ):
        config = LeaveSLAConfig.objects.filter(request_type="resumption").first()
        if config is None:
            break
        elapsed = now - resumption.assigned_at
        stage = f"resumption:{resumption.assigned_user_id}"
        if (config.reminder_after_hours is not None
                and elapsed >= timedelta(hours=config.reminder_after_hours)
                and resumption.reminder_sent_at is None):
            with transaction.atomic():
                locked = LeaveResumption.objects.select_for_update().get(pk=resumption.pk)
                if locked.status == "pending" and locked.reminder_sent_at is None:
                    LeaveSLAEvent.objects.create(
                        resumption=locked, event_type="reminder", stage_key=stage,
                    )
                    locked.reminder_sent_at = now
                    locked.save(update_fields=("reminder_sent_at",))
                    _notify(
                        locked.assigned_user_id, "leave.sla.reminder",
                        f"leave:resumption:{locked.pk}:reminder:{stage}",
                        "Leave resumption reminder",
                        f"Resumption request {locked.pk} is awaiting your review.",
                    )
                    reminders += 1
        if (config.escalation_after_hours is not None
                and elapsed >= timedelta(hours=config.escalation_after_hours)
                and resumption.escalation_sent_at is None):
            with transaction.atomic():
                locked = LeaveResumption.objects.select_for_update().get(pk=resumption.pk)
                if locked.status == "pending" and locked.escalation_sent_at is None:
                    recipient = config.escalation_user_id or locked.assigned_user_id
                    LeaveSLAEvent.objects.create(
                        resumption=locked, event_type="escalation", stage_key=stage,
                    )
                    if config.changes_assignment and config.escalation_user_id:
                        locked.assigned_user_id = config.escalation_user_id
                        locked.assigned_at = now
                        locked.reminder_sent_at = None
                    locked.escalation_sent_at = now
                    locked.save()
                    _notify(
                        recipient, "leave.sla.escalated",
                        f"leave:resumption:{locked.pk}:escalation:{stage}",
                        "Leave resumption escalation",
                        f"Resumption request {locked.pk} has passed its configured SLA.",
                    )
                    escalations += 1
    return {"reminders": reminders, "escalations": escalations}
