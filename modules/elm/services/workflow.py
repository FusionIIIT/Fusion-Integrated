"""Leave validation, accounting, and assigned approval transitions."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.domain.state_machine import validate_status_change
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    HolidayCalendar,
    LeaveAccount,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestEvent,
    LeaveTransaction,
    VacationPeriod,
)

ZERO = Decimal("0.00")
PENDING = (
    "awaiting_substitute",
    "applicant_action_required",
    "awaiting_unit_head",
    "awaiting_establishment",
    "awaiting_final_sanction",
    "awaiting_director_self",
)


def _policy(category: str) -> LeavePolicy:
    try:
        return LeavePolicy.objects.get(category=category)
    except LeavePolicy.DoesNotExist as exc:
        raise ValidationError({"category": "Leave policy is not configured."}) from exc


def _active_calendar(year: int) -> HolidayCalendar | None:
    return (
        HolidayCalendar.objects.filter(year=year, status="published")
        .order_by("-published_at", "-id")
        .first()
    )


def _employee(user_id: int) -> EmployeeProfile:
    try:
        return EmployeeProfile.objects.select_related("unit").get(user_id=user_id)
    except EmployeeProfile.DoesNotExist as exc:
        raise PermissionDenied("Your employee leave profile has not been configured.") from exc


def _account(user_id: int, category: str, year: int) -> LeaveAccount:
    profile = _employee(user_id)
    policy = _policy(category)
    eligible = (
        policy.faculty_eligible
        if profile.employee_kind == EmployeeProfile.FACULTY
        else policy.staff_eligible
    )
    if not eligible:
        raise ValidationError(
            {"category": "This leave category is not available to your employee group."}
        )
    annual = (
        policy.faculty_entitlement
        if profile.employee_kind == EmployeeProfile.FACULTY
        else policy.staff_entitlement
    )
    account, created = LeaveAccount.objects.select_for_update().get_or_create(
        employee_user_id=user_id,
        category=category,
        year=year,
        defaults={"entitlement": annual, "available_balance": ZERO},
    )
    if created:
        opening = ZERO
        if policy.carries_forward:
            previous = LeaveAccount.objects.filter(
                employee_user_id=user_id, category=category, year=year - 1
            ).first()
            if previous:
                opening = previous.available_balance
                if policy.max_carry_forward is not None:
                    opening = min(opening, policy.max_carry_forward)
        account.opening_balance = opening
        account.available_balance = opening + annual
        account.save(update_fields=["opening_balance", "available_balance", "updated_at"])
        if opening:
            LeaveTransaction.objects.create(
                account=account,
                amount=opening,
                kind="carry_forward",
                reference=f"carry:{user_id}:{category}:{year}",
                note="Opening carry-forward",
            )
        if annual:
            LeaveTransaction.objects.create(
                account=account,
                amount=annual,
                kind="annual_credit",
                reference=f"annual:{user_id}:{category}:{year}",
                note="Annual entitlement",
            )
    return account


def _chargeable_days(category: str, starts: date, ends: date, part: str = "") -> Decimal:
    policy = _policy(category)
    if ends < starts:
        raise ValidationError({"ends_on": "End date must be on or after start date."})
    if part and (category != "CL" or starts != ends or part not in ("first", "second")):
        raise ValidationError({"cl_part": "Half-day leave is available only for one CL date."})
    if category == "RH":
        cal = _active_calendar(starts.year)
        if (
            starts != ends
            or not cal
            or not cal.holidays.filter(date=starts, kind="restricted").exists()
        ):
            raise ValidationError(
                {"starts_on": "RH must match a date in the published RH calendar."}
            )
        return Decimal("1.00")
    if (
        category == "VL"
        and not VacationPeriod.objects.filter(starts_on__lte=starts, ends_on__gte=ends).exists()
    ):
        raise ValidationError(
            {"starts_on": "VL must fall within an Academic Calendar vacation period."}
        )
    if policy.continuous_count:
        days = (ends - starts).days + 1
    else:
        cal = _active_calendar(starts.year)
        public_holidays = set()
        if cal:
            public_holidays = set(
                cal.holidays.filter(kind="public", date__range=(starts, ends)).values_list(
                    "date", flat=True
                )
            )
        days = sum(
            1
            for offset in range((ends - starts).days + 1)
            if (d := starts + timedelta(days=offset)).weekday() < 5 and d not in public_holidays
        )
    result = Decimal(days) / Decimal("2") if part else Decimal(days)
    if result <= ZERO:
        raise ValidationError(
            {"starts_on": "The requested period contains no chargeable leave days."}
        )
    return result.quantize(Decimal("0.01"))


def _has_overlap(user_id: int, category: str, starts: date, ends: date, part: str = "") -> bool:
    active = LeaveRequest.objects.filter(
        employee_user_id=user_id,
        status__in=(*PENDING, "approved"),
        starts_on__lte=ends,
        ends_on__gte=starts,
    )
    for existing in active:
        if (
            category == "CL"
            and existing.category == "CL"
            and starts == ends == existing.starts_on == existing.ends_on
            and part
            and existing.cl_part
            and part != existing.cl_part
        ):
            continue
        return True
    return False


def _assert_substitute(user_id: int, substitute_id: int, starts: date, ends: date) -> None:
    if substitute_id == user_id:
        raise ValidationError({"substitute_user_id": "The substitute must be another employee."})
    if not EmployeeProfile.objects.filter(user_id=substitute_id).exists():
        raise ValidationError({"substitute_user_id": "Choose an active employee as substitute."})
    conflict = LeaveRequest.objects.filter(
        employee_user_id=substitute_id,
        status__in=(*PENDING, "approved"),
        starts_on__lte=ends,
        ends_on__gte=starts,
    ).exists()
    if conflict:
        raise ValidationError(
            {"substitute_user_id": "The substitute has overlapping pending or approved leave."}
        )


def _event(
    request: LeaveRequest, actor: int | None, action: str, to_status: str, note: str = ""
) -> None:
    before = request.status
    try:
        validate_status_change(before, to_status)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    request.status = to_status
    request.save()
    LeaveRequestEvent.objects.create(
        request=request,
        actor_user_id=actor,
        from_status=before,
        to_status=to_status,
        action=action,
        note=note,
    )


def _assign(request: LeaveRequest, *, user_id: int | None, stage: str, status: str) -> None:
    request.assigned_user_id = user_id
    request.assigned_stage = stage
    request.route_sequence = (
        request.route_sequence if stage not in ("unit_head", "substitute") else 0
    )
    request.task_assigned_at = timezone.now()
    request.reminder_sent_at = None
    request.escalation_sent_at = None
    _event(request, None, "assigned", status, f"Assigned to {stage}.")


def _route_queryset(request: LeaveRequest):
    profile = _employee(request.employee_user_id)
    local = ApprovalRoute.objects.filter(category=request.category, unit_id=profile.unit_id)
    if profile.designation:
        exact = local.filter(designation=profile.designation)
        if exact.exists():
            return exact.order_by("sequence")
    local = local.filter(designation="")
    if local.exists():
        return local.order_by("sequence")
    global_routes = ApprovalRoute.objects.filter(category=request.category, unit__isnull=True)
    if profile.designation:
        exact = global_routes.filter(designation=profile.designation)
        if exact.exists():
            return exact.order_by("sequence")
    return global_routes.filter(designation="").order_by("sequence")


def _next_route(request: LeaveRequest, after: int = 0):
    return _route_queryset(request).filter(sequence__gt=after).first()


def _assign_route(request: LeaveRequest, route: ApprovalRoute) -> None:
    request.route_sequence = route.sequence
    state = "awaiting_establishment" if route.is_establishment else "awaiting_final_sanction"
    _assign(
        request,
        user_id=route.authority_user_id,
        stage="establishment" if route.is_establishment else route.stage,
        status=state,
    )


def _deduct(request: LeaveRequest) -> None:
    account = _account(request.employee_user_id, request.category, request.starts_on.year)
    if account.available_balance < request.chargeable_days:
        raise ValidationError(
            {"category": "Leave balance changed before approval; the request cannot be approved."}
        )
    account.available_balance -= request.chargeable_days
    account.save(update_fields=["available_balance", "updated_at"])
    LeaveTransaction.objects.create(
        account=account,
        request=request,
        amount=-request.chargeable_days,
        kind="leave_debit",
        reference=f"request:{request.pk}:debit",
    )


@transaction.atomic
def submit_leave(actor_id: int, data: dict) -> LeaveRequest:
    profile = _employee(actor_id)
    category = data["category"]
    starts, ends = data["starts_on"], data["ends_on"]
    policy = _policy(category)
    days = _chargeable_days(category, starts, ends, data.get("cl_part", ""))
    if policy.requires_medical_evidence and not data.get("medical_evidence_reference"):
        raise ValidationError(
            {"medical_evidence_reference": "Medical evidence is required for this leave."}
        )
    if data.get("station_leave") and not data.get("station_details", "").strip():
        raise ValidationError(
            {"station_details": "Station Leave details are required when applicable."}
        )
    if _has_overlap(actor_id, category, starts, ends, data.get("cl_part", "")):
        raise ValidationError(
            {"starts_on": "This period overlaps an active pending or approved leave."}
        )
    account = _account(actor_id, category, starts.year)
    reserved = (
        LeaveRequest.objects.filter(
            employee_user_id=actor_id,
            category=category,
            status__in=PENDING,
            starts_on__year=starts.year,
        ).aggregate(total=Sum("chargeable_days"))["total"]
        or ZERO
    )
    if account.available_balance - reserved < days:
        raise ValidationError({"category": "The available leave balance is insufficient."})
    substitute = data.get("substitute_user_id")
    if policy.requires_substitute and not substitute:
        raise ValidationError({"substitute_user_id": "A substitute is required for this leave."})
    if substitute:
        _assert_substitute(actor_id, substitute, starts, ends)
    if (
        not substitute
        and not profile.unit.unit_head_user_id
        and not any(
            "director" in role.casefold() for role in getattr(data.get("actor"), "roles", ())
        )
    ):
        raise ValidationError("The employee's Unit Head has not been configured.")
    obj = LeaveRequest.objects.create(
        employee_user_id=actor_id,
        category=category,
        starts_on=starts,
        ends_on=ends,
        chargeable_days=days,
        cl_part=data.get("cl_part", ""),
        reason=data["reason"].strip(),
        medical_evidence_reference=data.get("medical_evidence_reference", "").strip(),
        station_leave=data.get("station_leave", False),
        station_details=data.get("station_details", "").strip(),
        substitute_user_id=substitute,
        submitted_at=timezone.now(),
        director_self_sanction=any(
            "director" in role.casefold() for role in getattr(data.get("actor"), "roles", ())
        ),
    )
    LeaveRequestEvent.objects.create(
        request=obj, actor_user_id=actor_id, to_status=obj.status, action="submitted"
    )
    if substitute:
        _assign(obj, user_id=substitute, stage="substitute", status="awaiting_substitute")
    elif any("director" in role.casefold() for role in getattr(data.get("actor"), "roles", ())):
        _assign(
            obj, user_id=actor_id, stage="director_self_sanction", status="awaiting_director_self"
        )
    else:
        _assign(
            obj,
            user_id=profile.unit.unit_head_user_id,
            stage="unit_head",
            status="awaiting_unit_head",
        )
    return obj


def _require_assignee(request: LeaveRequest, actor_id: int) -> None:
    if request.assigned_user_id != actor_id:
        raise PermissionDenied("This workflow action is assigned to another user.")


def _start_review(request: LeaveRequest, actor_id: int, note: str = "") -> None:
    if request.category in ("CL", "RH"):
        request.decided_at = timezone.now()
        request.decision_reason = note
        _deduct(request)
        _event(request, actor_id, "approved", "approved", note)
        return
    route = _next_route(request)
    if route is None:
        raise ValidationError(
            "No higher-sanction approval route is configured for this unit and leave category."
        )
    request.unit_head_recommendation = "recommended" if note == "recommended" else "not_recommended"
    request.save(update_fields=["unit_head_recommendation", "updated_at"])
    _assign_route(request, route)


@transaction.atomic
def act(
    actor_id: int, request_id: int, action: str, note: str = "", substitute_id: int | None = None
) -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if action == "withdraw":
        if req.employee_user_id != actor_id or req.status not in PENDING:
            raise PermissionDenied(
                "Only the applicant may withdraw a request before its final decision."
            )
        _event(req, actor_id, "withdrawn", "withdrawn", note)
        req.assigned_user_id = None
        req.decided_at = timezone.now()
        req.save(update_fields=["assigned_user_id", "decided_at", "updated_at"])
        return req
    if req.status not in PENDING:
        raise ValidationError("This request no longer accepts workflow actions.")
    _require_assignee(req, actor_id)
    if action == "reject" and not note.strip():
        raise ValidationError({"note": "A reason is required when rejecting a request."})

    if req.assigned_stage == "substitute":
        if action not in ("accept_substitute", "decline_substitute"):
            raise ValidationError({"action": "Choose accept_substitute or decline_substitute."})
        if action == "decline_substitute":
            _event(req, actor_id, action, "applicant_action_required", note)
            req.assigned_user_id = req.employee_user_id
            req.assigned_stage = "replacement_substitute"
            req.save(update_fields=["assigned_user_id", "assigned_stage", "updated_at"])
        else:
            profile = _employee(req.employee_user_id)
            if req.director_self_sanction or "director" in profile.designation.casefold():
                _assign(
                    req,
                    user_id=req.employee_user_id,
                    stage="director_self_sanction",
                    status="awaiting_director_self",
                )
            else:
                if not profile.unit.unit_head_user_id:
                    raise ValidationError("The employee's Unit Head has not been configured.")
                _assign(
                    req,
                    user_id=profile.unit.unit_head_user_id,
                    stage="unit_head",
                    status="awaiting_unit_head",
                )
        return req

    if req.assigned_stage == "replacement_substitute":
        if action != "replace_substitute" or substitute_id is None:
            raise ValidationError(
                {"substitute_user_id": "Choose an eligible replacement employee."}
            )
        _assert_substitute(req.employee_user_id, substitute_id, req.starts_on, req.ends_on)
        req.substitute_user_id = substitute_id
        req.save(update_fields=["substitute_user_id", "updated_at"])
        _assign(req, user_id=substitute_id, stage="substitute", status="awaiting_substitute")
        return req

    if req.assigned_stage == "unit_head":
        if req.category in ("CL", "RH"):
            if action not in ("approve", "reject"):
                raise ValidationError({"action": "Unit Head must approve or reject CL/RH."})
            if action == "reject":
                req.decided_at = timezone.now()
                req.decision_reason = note
                _event(req, actor_id, action, "rejected", note)
            else:
                _start_review(req, actor_id, note)
            return req
        if action not in ("recommended", "not_recommended"):
            raise ValidationError(
                {"action": "Unit Head must record recommended or not_recommended."}
            )
        _start_review(req, actor_id, action)
        return req

    if req.assigned_stage == "establishment":
        if action != "verify":
            raise ValidationError({"action": "Establishment must verify and route this request."})
        next_route = _next_route(req, req.route_sequence)
        if not next_route:
            raise ValidationError("No next sanctioning authority is configured.")
        _assign_route(req, next_route)
        return req

    if req.status in ("awaiting_final_sanction", "awaiting_director_self"):
        if action not in ("approve", "reject"):
            raise ValidationError({"action": "Choose approve or reject."})
        req.decided_at = timezone.now()
        req.decision_reason = note
        if action == "reject":
            _event(req, actor_id, action, "rejected", note)
            return req
        _deduct(req)
        _event(req, actor_id, "approved", "approved", note)
        return req

    raise ValidationError("This request has no actionable workflow stage.")


def balances_for(user_id: int, year: int | None = None) -> list[dict]:
    year = year or timezone.localdate().year
    _employee(user_id)
    rows = []
    for policy in LeavePolicy.objects.order_by("category"):
        try:
            account = _account(user_id, policy.category, year)
        except ValidationError:
            continue
        reserved = (
            LeaveRequest.objects.filter(
                employee_user_id=user_id,
                category=policy.category,
                status__in=PENDING,
                starts_on__year=year,
            ).aggregate(total=Sum("chargeable_days"))["total"]
            or ZERO
        )
        rows.append(
            {
                "category": policy.category,
                "year": year,
                "entitlement": account.entitlement,
                "opening_balance": account.opening_balance,
                "available": account.available_balance,
                "pending": reserved,
                "spendable": max(ZERO, account.available_balance - reserved),
            }
        )
    return rows
