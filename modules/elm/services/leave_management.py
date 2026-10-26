"""Policy validation, routing, account posting and lifecycle transitions."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    LeaveAccount,
    LeaveAuditEvent,
    LeaveCalendarDate,
    LeaveCase,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
)
from modules.elm.services import notifications

ACTIVE_STATUSES = (
    "awaiting_substitute", "pending_unit_head", "pending_sanction", "approved",
)
PENDING_STATUSES = ("awaiting_substitute", "pending_unit_head", "pending_sanction")
HIGHER_SANCTION = {"SCL", "EL", "COL", "VL"}
ZERO = Decimal("0")


def _permission(actor, code: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check and check(code))


def _require(actor, code: str) -> None:
    if not _permission(actor, code):
        raise PermissionDeniedError(
            "This action needs an ELM permission.", code="permission_denied")


def _profile(user_id: int) -> EmployeeProfile:
    try:
        profile = EmployeeProfile.objects.select_related("organization_unit").get(
            user_id=user_id, is_active=True)
    except EmployeeProfile.DoesNotExist as exc:
        raise ConflictError(
            "An active ELM employee profile must be configured before leave can be processed.",
            code="employee_profile_missing") from exc
    return profile


def _working_dates(start: date, end: date) -> list[date]:
    closed = set(LeaveCalendarDate.objects.filter(
        kind="closed_holiday", is_published=True, date__range=(start, end),
    ).values_list("date", flat=True))
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in closed:
            days.append(current)
        current += timedelta(days=1)
    return days


def _days_by_year(category: str, start: date, end: date,
                  half_day: str = "none") -> dict[int, Decimal]:
    policy = LeavePolicy.objects.get(category=category, is_active=True)
    if category == "RH":
        return {start.year: Decimal("1")}
    if category == "CL" and half_day != "none":
        return {start.year: Decimal("0.5")}
    if policy.continuous_days:
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)
    else:
        dates = _working_dates(start, end)
    result: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for day in dates:
        result[day.year] += Decimal("1")
    return dict(result)


def _account(user_id: int, category: str, year: int,
             employee_type: str) -> LeaveAccount:
    policy = LeavePolicy.objects.filter(category=category, is_active=True).first()
    if policy is None:
        raise ConflictError(f"No active policy is configured for {category}.",
                            code="leave_policy_missing")
    account, created = LeaveAccount.objects.get_or_create(
        user_id=user_id, category=category, year=year)
    if created:
        opening = ZERO
        if policy.carry_forward:
            prior = LeaveAccount.objects.filter(
                user_id=user_id, category=category, year=year - 1).first()
            if prior:
                opening = max(ZERO, prior.balance)
        annual_credit = policy.annual_entitlement
        if policy.faculty_only and employee_type != "faculty":
            annual_credit = ZERO
        if category == "EL" and employee_type == "faculty":
            annual_credit = ZERO
        account.opening_balance = opening
        account.credited = annual_credit
        account.closing_balance = opening + annual_credit
        account.save(update_fields=[
            "opening_balance", "credited", "closing_balance", "updated_at",
        ])
        if annual_credit:
            LeaveTransaction.objects.create(
                user_id=user_id, category=category, amount=annual_credit,
                transaction_type="annual_credit",
                description=f"{year} annual {category} entitlement")
    return account


def _refresh_account(account: LeaveAccount) -> LeaveAccount:
    account.closing_balance = account.balance
    account.save(update_fields=[
        "opening_balance", "credited", "used", "lapsed", "closing_balance",
        "updated_at",
    ])
    return account


def _charge(user_id: int, employee_type: str, category: str,
            amounts: dict[int, Decimal], request: LeaveRequest,
            actor_id: int, transaction_type: str = "leave_debit") -> None:
    accounts = []
    for year, amount in amounts.items():
        account = _account(user_id, category, year, employee_type)
        available = account.balance - _reserved_days(
            user_id, category, year, request.id)
        if available < amount:
            raise ConflictError(
                f"Insufficient {category} balance for {year}; "
                f"{amount} day(s) requested, {available} available after "
                "pending requests.",
                code="insufficient_leave_balance")
        account.used += amount
        _refresh_account(account)
        accounts.append((year, amount))
    for year, amount in accounts:
        LeaveTransaction.objects.create(
            user_id=user_id, category=category, amount=-amount,
            transaction_type=transaction_type, reference_request=request,
            performed_by_user_id=actor_id,
            description=f"{category} leave for {year}")


def _audit(leave: LeaveRequest, actor_id: int, action: str,
           note: str = "", case: LeaveCase | None = None) -> None:
    LeaveAuditEvent.objects.create(
        leave_request=leave, case=case, actor_user_id=actor_id,
        action=action, note=note)


def _notify(user_id: int | None, topic: str, key: str,
            subject: str, body: str) -> None:
    if user_id is not None:
        notifications.enqueue(
            topic=topic, dedupe_key=key, recipient_user_id=user_id,
            subject=subject, body=body)


def _route(category: str, profile: EmployeeProfile) -> ApprovalRoute:
    candidates = ApprovalRoute.objects.filter(
        category=category, is_active=True).filter(
            Q(organization_unit=profile.organization_unit)
            | Q(organization_unit__isnull=True))
    route = candidates.filter(
        organization_unit=profile.organization_unit).first()
    if route is None:
        route = candidates.filter(organization_unit__isnull=True).first()
    if route is None:
        raise ConflictError(
            f"No final-sanction route is configured for {category}.",
            code="approval_route_missing")
    return route


def _assign_sanction(target: LeaveRequest | LeaveCase,
                     profile: EmployeeProfile, category: str) -> None:
    route = _route(category, profile)
    target.status = "pending_sanction"
    target.assigned_user_id = route.approver_user_id
    target.assigned_role = "" if route.establishment_required else route.approver_role
    target.assigned_permission = (
        "elm.leave.process" if route.establishment_required
        else route.permission_code)
    if isinstance(target, LeaveRequest):
        target.workflow_stage = (
            "establishment" if route.establishment_required else "sanction")
    target.save(update_fields=[
        "status", "assigned_user_id", "assigned_permission", "assigned_role",
        "updated_at",
        *(["workflow_stage"] if isinstance(target, LeaveRequest) else []),
    ])
    _notify(
        target.assigned_user_id, "leave.action_required",
        f"leave.sanction_assigned:{target.pk}:{target.updated_at.isoformat()}",
        f"Leave request #{target.pk} requires sanction",
        f"A {category} leave request is assigned to you for final sanction.")


def _assign_unit_head(target: LeaveRequest | LeaveCase,
                      profile: EmployeeProfile) -> None:
    if profile.designation.strip().casefold() == "director":
        target.status = "pending_sanction"
        target.assigned_user_id = profile.user_id
        target.assigned_permission = "elm.leave.sanction"
        target.assigned_role = "Director"
        if isinstance(target, LeaveRequest):
            target.workflow_stage = "sanction"
        target.save(update_fields=[
            "status", "assigned_user_id", "assigned_permission", "assigned_role",
            "updated_at",
            *(["workflow_stage"] if isinstance(target, LeaveRequest) else []),
        ])
        leave = target if isinstance(target, LeaveRequest) else target.leave_request
        _notify(
            profile.user_id, "leave.action_required",
            f"leave.director_self_sanction:{target.pk}:{target.updated_at.isoformat()}",
            f"Director leave request #{leave.pk} requires self-sanction",
            f"Your {leave.category} leave request from {leave.start_date} to "
            f"{leave.end_date} is assigned for self-sanction.")
        return
    unit = profile.organization_unit
    if unit is None or unit.unit_head_user_id is None:
        raise ConflictError(
            "The employee's organization unit must have a configured Unit Head.",
            code="unit_head_missing")
    target.status = "pending_unit_head"
    target.assigned_user_id = unit.unit_head_user_id
    target.assigned_permission = "elm.leave.review"
    target.assigned_role = ""
    if isinstance(target, LeaveRequest):
        target.workflow_stage = "unit_head"
    target.save(update_fields=[
        "status", "assigned_user_id", "assigned_permission", "assigned_role",
        "updated_at",
        *(["workflow_stage"] if isinstance(target, LeaveRequest) else []),
    ])
    leave = target if isinstance(target, LeaveRequest) else target.leave_request
    start = target.requested_start if isinstance(target, LeaveCase) else leave.start_date
    end = target.requested_end if isinstance(target, LeaveCase) else leave.end_date
    _notify(
        target.assigned_user_id, "leave.action_required",
        f"leave.unit_head_assigned:{target.pk}:{target.updated_at.isoformat()}",
        f"Leave request #{leave.pk} requires Unit Head review",
        f"A {leave.category} leave request for {start or leave.start_date} to "
        f"{end or leave.end_date} is assigned to you.")


def _assert_assigned(actor, target: LeaveRequest | LeaveCase) -> None:
    if target.assigned_role and target.assigned_role not in getattr(actor, "roles", ()):
        raise PermissionDeniedError("This task is assigned to another ELM role.")
    if target.assigned_user_id is not None:
        if actor.user_id != target.assigned_user_id:
            raise PermissionDeniedError("This task is assigned to another user.")
    elif not _permission(actor, target.assigned_permission):
        raise PermissionDeniedError("This task is not assigned to your role.")


def _validate_period(category: str, start: date, end: date, half_day: str,
                     employee_type: str, user_id: int,
                     exclude_request_id: int | None = None) -> dict[int, Decimal]:
    if end < start:
        raise ConflictError("The end date must be on or after the start date.",
                            code="invalid_leave_dates")
    policy = LeavePolicy.objects.filter(category=category, is_active=True).first()
    if policy is None:
        raise ConflictError(f"No active policy is configured for {category}.",
                            code="leave_policy_missing")
    if policy.faculty_only and employee_type != "faculty":
        raise ConflictError(f"{category} is available to faculty only.",
                            code="leave_category_not_applicable")
    if half_day != "none" and (
        category != "CL" or not policy.allow_half_day or start != end
    ):
        raise ConflictError(
            "Half-day requests are available only for a single-day CL request.",
            code="invalid_half_day")
    if category == "RH" and (
        start != end or not LeaveCalendarDate.objects.filter(
            date=start, kind="restricted_holiday", is_published=True,
        ).exists()
    ):
        raise ConflictError(
            "RH must be requested for a published Restricted Holiday date.",
            code="restricted_holiday_required")
    if category == "CL" and not _working_dates(start, end):
        raise ConflictError("CL must fall on a working day.",
                            code="no_chargeable_leave_days")
    if category == "VL":
        vacation_dates = set(LeaveCalendarDate.objects.filter(
            kind="vacation", is_published=True, date__range=(start, end),
        ).values_list("date", flat=True))
        if any(day not in vacation_dates for day in _date_range(start, end)):
            raise ConflictError(
                "VL may be used only during a published vacation period.",
                code="vacation_period_required")
    active = LeaveRequest.objects.filter(
        applicant_user_id=user_id, status__in=ACTIVE_STATUSES,
        start_date__lte=end, end_date__gte=start)
    if exclude_request_id:
        active = active.exclude(pk=exclude_request_id)
    for existing in active:
        half_exception = (
            category == "CL" and existing.category == "CL"
            and start == end == existing.start_date == existing.end_date
            and half_day != "none" and existing.half_day != "none"
            and half_day != existing.half_day
        )
        if not half_exception:
            raise ConflictError(
                "The requested dates overlap another pending or approved leave.",
                code="leave_overlap")
    extensions = LeaveCase.objects.filter(
        leave_request__applicant_user_id=user_id,
        case_type="extension", status__in=(*PENDING_STATUSES, "approved"),
        requested_start__lte=end, requested_end__gte=start,
    )
    if exclude_request_id:
        extensions = extensions.exclude(leave_request_id=exclude_request_id)
    if extensions.exists():
        raise ConflictError(
            "The requested dates overlap another approved leave extension.",
            code="leave_overlap")
    # Enforce Business Rule: Casual Leave cannot be combined in continuation with other leave types
    if category == "CL":
        adjacent = LeaveRequest.objects.filter(
            applicant_user_id=user_id, status__in=ACTIVE_STATUSES,
        ).exclude(category__in={"CL", "RH"}).filter(
            Q(end_date=start - timedelta(days=1)) | Q(start_date=end + timedelta(days=1))
        )
        if exclude_request_id:
            adjacent = adjacent.exclude(pk=exclude_request_id)
        if adjacent.exists():
            raise ConflictError(
                "Casual Leave (CL) cannot be combined in continuation with other leave categories.",
                code="invalid_leave_combination")
    elif category not in {"CL", "RH"}:
        adjacent = LeaveRequest.objects.filter(
            applicant_user_id=user_id, category="CL", status__in=ACTIVE_STATUSES,
        ).filter(
            Q(end_date=start - timedelta(days=1)) | Q(start_date=end + timedelta(days=1))
        )
        if exclude_request_id:
            adjacent = adjacent.exclude(pk=exclude_request_id)
        if adjacent.exists():
            raise ConflictError(
                "Cannot combine this leave category with adjacent Casual Leave (CL).",
                code="invalid_leave_combination")

    amounts = _days_by_year(category, start, end, half_day)
    if not amounts or any(amount <= ZERO for amount in amounts.values()):
        raise ConflictError("The selected period contains no chargeable leave days.",
                            code="no_chargeable_leave_days")
    for year, amount in amounts.items():
        account = _account(user_id, category, year, employee_type)
        available = account.balance - _reserved_days(
            user_id, category, year, exclude_request_id)
        if available < amount:
            raise ConflictError(
                f"Insufficient {category} balance for {year}; "
                f"{amount} day(s) requested, {available} available after pending requests.",
                code="insufficient_leave_balance")
    return amounts


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _reserved_days(user_id: int, category: str, year: int,
                   exclude_request_id: int | None) -> Decimal:
    reserved = ZERO
    pending = LeaveRequest.objects.filter(
        applicant_user_id=user_id, category=category,
        status__in=PENDING_STATUSES)
    if exclude_request_id:
        pending = pending.exclude(pk=exclude_request_id)
    for request in pending:
        reserved += _days_by_year(
            category, request.start_date, request.end_date,
            request.half_day).get(year, ZERO)
    extensions = LeaveCase.objects.filter(
        leave_request__applicant_user_id=user_id,
        leave_request__category=category,
        case_type="extension", status__in=PENDING_STATUSES,
        requested_start__isnull=False, requested_end__isnull=False,
    )
    if exclude_request_id:
        extensions = extensions.exclude(leave_request_id=exclude_request_id)
    for case in extensions:
        reserved += _days_by_year(
            category, case.requested_start, case.requested_end).get(year, ZERO)
    return reserved


def _effective_end(leave: LeaveRequest) -> date:
    extension_end = LeaveCase.objects.filter(
        leave_request=leave, case_type="extension", status="approved",
        requested_end__isnull=False,
    ).order_by("-requested_end").values_list("requested_end", flat=True).first()
    return max(leave.end_date, extension_end) if extension_end else leave.end_date


@transaction.atomic
def apply_for_leave(actor, data: dict) -> LeaveRequest:
    _require(actor, "elm.leave.apply")
    profile = _profile(actor.user_id)
    category = data["category"]
    start, end = data["start_date"], data["end_date"]
    half_day = data.get("half_day", "none")
    amounts = _validate_period(
        category, start, end, half_day, profile.employee_type, actor.user_id)
    policy = LeavePolicy.objects.get(category=category)
    if policy.medical_evidence_required and not data.get("medical_evidence_ref"):
        raise ConflictError(
            "Supporting medical evidence is required for this request.",
            code="medical_evidence_required")
    if data.get("station_leave") and not data.get("station_destination", "").strip():
        raise ConflictError(
            "Enter the destination when requesting Station Leave.",
            code="station_destination_required")
    substitute_id = data.get("substitute_user_id")
    if substitute_id is not None:
        if substitute_id == actor.user_id:
            raise ConflictError("You cannot nominate yourself as substitute.",
                                code="invalid_substitute")
        substitute = _profile(substitute_id)
        if not substitute.is_active:
            raise ConflictError("The nominated substitute is inactive.",
                                code="invalid_substitute")
        if LeaveRequest.objects.filter(
            applicant_user_id=substitute_id, status__in=ACTIVE_STATUSES,
            start_date__lte=end, end_date__gte=start,
        ).exists():
            raise ConflictError(
                "The nominated substitute has overlapping leave.",
                code="substitute_unavailable")
    leave = LeaveRequest.objects.create(
        applicant_user_id=actor.user_id, category=category,
        start_date=start, end_date=end, half_day=half_day,
        purpose=data["purpose"].strip(),
        station_leave=data.get("station_leave", False),
        station_destination=data.get("station_destination", "").strip(),
        medical_evidence_ref=data.get("medical_evidence_ref", "").strip(),
        substitute_user_id=substitute_id,
        substitute_response="pending" if substitute_id else "",
        status="awaiting_substitute" if substitute_id else "pending_unit_head",
        workflow_stage="substitute" if substitute_id else "unit_head",
        approved_days=sum(amounts.values(), ZERO),
    )
    if substitute_id:
        leave.assigned_user_id = substitute_id
        leave.assigned_permission = "elm.leave.substitute_respond"
        leave.assigned_role = ""
        leave.save(update_fields=["assigned_user_id", "assigned_permission",
                                  "assigned_role", "updated_at"])
    else:
        _assign_unit_head(leave, profile)
    if substitute_id:
        _notify(
            substitute_id, "leave.action_required",
            f"leave.substitute_assigned:{leave.pk}:{leave.updated_at.isoformat()}",
            f"Substitute response requested for leave #{leave.pk}",
            f"You have been nominated for responsibility coverage on a "
            f"{category} leave request from {start} to {end}.")
    _audit(leave, actor.user_id, "submitted")
    return leave


def request_for_actor(actor, request_id: int) -> LeaveRequest:
    leave = LeaveRequest.objects.filter(pk=request_id).first()
    if leave is None:
        raise NotFoundError("Leave request not found.")
    if leave.applicant_user_id == actor.user_id:
        return leave
    if _permission(actor, "elm.leave.view_all"):
        return leave
    if (leave.assigned_user_id == actor.user_id
            and _permission(actor, leave.assigned_permission)
            and (not leave.assigned_role
                 or leave.assigned_role in getattr(actor, "roles", ()))):
        return leave
    if _permission(actor, "elm.leave.review") and leave.status == "pending_unit_head":
        profile = EmployeeProfile.objects.filter(
            user_id=leave.applicant_user_id).select_related("organization_unit").first()
        if (profile and profile.organization_unit
                and profile.organization_unit.unit_head_user_id == actor.user_id):
            return leave
    raise NotFoundError("Leave request not found.")


def _finalize_leave(leave: LeaveRequest, actor_id: int, approve: bool,
                    note: str, profile: EmployeeProfile) -> None:
    if approve:
        amounts = _days_by_year(
            leave.category, leave.start_date, leave.end_date, leave.half_day)
        _charge(leave.applicant_user_id, profile.employee_type, leave.category,
                amounts, leave, actor_id)
        leave.status = "approved"
        leave.decided_at = timezone.now()
        leave.approved_days = sum(amounts.values(), ZERO)
        action = "approved"
    else:
        leave.status = "rejected"
        leave.decided_at = timezone.now()
        action = "rejected"
    leave.assigned_user_id = None
    leave.assigned_permission = ""
    leave.assigned_role = ""
    leave.workflow_stage = ""
    leave.save(update_fields=[
        "status", "decided_at", "approved_days", "assigned_user_id",
        "assigned_permission", "workflow_stage", "updated_at",
    ])
    _audit(leave, actor_id, action, note)
    _notify(
        leave.applicant_user_id, "leave.decision",
        f"leave.decision:{leave.pk}:{action}",
        f"Leave request #{leave.pk} {action}",
        f"Your {leave.category} leave request for {leave.start_date} to "
        f"{leave.end_date} was {action}.")


@transaction.atomic
def decide_leave(actor, leave: LeaveRequest, action: str, note: str = "") -> LeaveRequest:
    if leave.status not in PENDING_STATUSES:
        raise ConflictError("This request is no longer awaiting a decision.",
                            code="leave_not_pending")
    _assert_assigned(actor, leave)
    profile = _profile(leave.applicant_user_id)
    if leave.status == "awaiting_substitute":
        _require(actor, "elm.leave.substitute_respond")
        if actor.user_id != leave.substitute_user_id:
            raise PermissionDeniedError("Only the nominated substitute may respond.")
        if action not in {"accept", "decline"}:
            raise ConflictError("Substitute response must be accept or decline.")
        leave.substitute_response = "accepted" if action == "accept" else "declined"
        if action == "accept":
            _assign_unit_head(leave, profile)
        else:
            leave.status = "awaiting_substitute"
            leave.workflow_stage = "applicant_action_required"
            leave.assigned_user_id = leave.applicant_user_id
            leave.assigned_permission = "elm.leave.apply"
            leave.assigned_role = ""
            leave.save(update_fields=[
                "status", "workflow_stage", "assigned_user_id",
                "assigned_permission", "assigned_role", "substitute_response",
                "updated_at",
            ])
            _notify(
                leave.applicant_user_id, "leave.substitute_declined",
                f"leave.substitute_declined:{leave.pk}:{leave.updated_at.isoformat()}",
                f"Substitute declined leave request #{leave.pk}",
                "Nominate another substitute or withdraw your pending request.")
        _audit(leave, actor.user_id, f"substitute_{action}", note)
        return leave

    if leave.status == "pending_unit_head":
        _require(actor, "elm.leave.review")
        unit = profile.organization_unit
        if unit is None or unit.unit_head_user_id != actor.user_id:
            raise PermissionDeniedError("Only the applicant's Unit Head may review.")
        if leave.category in {"CL", "RH"}:
            if action not in {"approve", "reject"}:
                raise ConflictError("Unit Head must make the final approve/reject decision.")
            _finalize_leave(leave, actor.user_id, action == "approve", note, profile)
        else:
            if action not in {"recommend", "not_recommended"}:
                raise ConflictError(
                    "Unit Head must record Recommended or Not Recommended.")
            _audit(leave, actor.user_id, action, note)
            _assign_sanction(leave, profile, leave.category)
        return leave

    _require(actor, leave.assigned_permission or "elm.leave.sanction")
    if action == "forward" and leave.workflow_stage == "establishment":
        _require(actor, "elm.leave.process")
        _assign_sanction(leave, profile, leave.category)
        _audit(leave, actor.user_id, action, note)
        return leave
    if actor.user_id == leave.applicant_user_id:
        if profile.designation.strip().casefold() != "director":
            raise PermissionDeniedError("Applicants cannot decide their own requests.")
        _require(actor, "elm.leave.sanction")
    if action not in {"approve", "reject"}:
        raise ConflictError("The sanctioning authority must approve or reject.")
    _finalize_leave(leave, actor.user_id, action == "approve", note, profile)
    return leave


@transaction.atomic
def withdraw(actor, leave: LeaveRequest) -> LeaveRequest:
    _require(actor, "elm.leave.withdraw")
    if leave.applicant_user_id != actor.user_id:
        raise PermissionDeniedError("You may withdraw only your own request.")
    if leave.status not in PENDING_STATUSES:
        raise ConflictError("Only a pending request can be withdrawn.",
                            code="leave_not_withdrawable")
    previous_assignee = leave.assigned_user_id
    leave.status = "withdrawn"
    leave.assigned_user_id = None
    leave.assigned_permission = ""
    leave.assigned_role = ""
    leave.workflow_stage = ""
    leave.save(update_fields=[
        "status", "assigned_user_id", "assigned_permission", "workflow_stage",
        "assigned_role", "updated_at",
    ])
    _audit(leave, actor.user_id, "withdrawn")
    _notify(
        previous_assignee, "leave.withdrawn",
        f"leave.withdrawn:{leave.pk}",
        f"Leave request #{leave.pk} was withdrawn",
        f"Leave request #{leave.pk} has been withdrawn and requires no further action.")
    _notify(
        leave.substitute_user_id, "leave.withdrawn",
        f"leave.substitute_withdrawn:{leave.pk}",
        f"Leave request #{leave.pk} was withdrawn",
        "The applicant withdrew the request; the substitute assignment is closed.")
    return leave


@transaction.atomic
def replace_substitute(actor, leave: LeaveRequest, substitute_id: int) -> LeaveRequest:
    _require(actor, "elm.leave.apply")
    if (leave.applicant_user_id != actor.user_id
            or leave.workflow_stage != "applicant_action_required"):
        raise ConflictError("This request is not awaiting a substitute replacement.")
    if substitute_id == actor.user_id:
        raise ConflictError("You cannot nominate yourself as substitute.",
                            code="invalid_substitute")
    substitute = _profile(substitute_id)
    if LeaveRequest.objects.filter(
        applicant_user_id=substitute_id, status__in=ACTIVE_STATUSES,
        start_date__lte=leave.end_date, end_date__gte=leave.start_date,
    ).exists():
        raise ConflictError("The nominated substitute has overlapping leave.",
                            code="substitute_unavailable")
    leave.substitute_user_id = substitute.user_id
    leave.substitute_response = "pending"
    leave.status = "awaiting_substitute"
    leave.workflow_stage = "substitute"
    leave.assigned_user_id = substitute.user_id
    leave.assigned_permission = "elm.leave.substitute_respond"
    leave.assigned_role = ""
    leave.save(update_fields=[
        "substitute_user_id", "substitute_response", "status",
        "workflow_stage", "assigned_user_id", "assigned_permission",
        "assigned_role",
        "updated_at",
    ])
    _audit(leave, actor.user_id, "substitute_reassigned")
    return leave


def _case_for_actor(actor, case_id: int) -> LeaveCase:
    case = LeaveCase.objects.select_related("leave_request").filter(pk=case_id).first()
    if case is None:
        raise NotFoundError("Leave action not found.")
    if case.leave_request.applicant_user_id == actor.user_id:
        return case
    if (case.assigned_user_id == actor.user_id
            and (not case.assigned_role
                 or case.assigned_role in getattr(actor, "roles", ()))) or (
        case.assigned_user_id is None and _permission(actor, case.assigned_permission)
    ):
        return case
    if _permission(actor, "elm.leave.view_all"):
        return case
    raise NotFoundError("Leave action not found.")


@transaction.atomic
def create_case(actor, leave: LeaveRequest, case_type: str,
                data: dict) -> LeaveCase:
    _require(actor, "elm.leave.apply")
    if leave.applicant_user_id != actor.user_id:
        raise PermissionDeniedError("You may act only on your own leave.")
    profile = _profile(actor.user_id)
    if case_type == "cancellation":
        if leave.status != "approved" or leave.start_date <= timezone.localdate():
            raise ConflictError(
                "Cancellation is available only before approved leave begins.",
                code="cancellation_not_available")
    elif case_type == "extension":
        effective_end = _effective_end(leave)
        if (leave.status != "approved" or leave.category not in {"EL", "COL", "VL"}
                or not (leave.start_date <= timezone.localdate() <= effective_end)):
            raise ConflictError(
                "Only ongoing EL, COL or VL can be extended.",
                code="extension_not_available")
        start = data["requested_start"]
        end = data["requested_end"]
        if start != effective_end + timedelta(days=1):
            raise ConflictError(
                "An extension must begin the day after the currently approved end date.",
                code="invalid_extension_period")
        _validate_period(leave.category, start, end, "none",
                         profile.employee_type, actor.user_id, leave.pk)
        policy = LeavePolicy.objects.get(category=leave.category)
        if policy.medical_evidence_required and not data.get("medical_evidence_ref"):
            raise ConflictError(
                "Supporting medical evidence is required for this request.",
                code="medical_evidence_required")
    elif case_type == "resumption":
        if (leave.status != "approved" or leave.category not in {"EL", "COL", "VL"}
                or leave.start_date > timezone.localdate()):
            raise ConflictError(
                "Resumption is available only for approved EL, COL or VL.",
                code="resumption_not_available")
        actual = data["actual_resumption_date"]
        if actual < leave.start_date:
            raise ConflictError(
                "The actual resumption date cannot be before leave begins.",
                code="invalid_resumption_date")
    else:
        raise ConflictError("Unsupported leave action.", code="invalid_case_type")
    if LeaveCase.objects.filter(
        leave_request=leave, case_type=case_type,
        status__in=("pending_unit_head", "pending_sanction"),
    ).exists():
        raise ConflictError("A request of this type is already pending.",
                            code="leave_case_pending")
    substitute_id = data.get("substitute_user_id")
    if substitute_id is not None:
        if substitute_id == actor.user_id:
            raise ConflictError("You cannot nominate yourself as substitute.",
                                code="invalid_substitute")
        _profile(substitute_id)
        period_start = data.get("requested_start") or leave.start_date
        period_end = data.get("requested_end") or _effective_end(leave)
        if LeaveRequest.objects.filter(
            applicant_user_id=substitute_id, status__in=ACTIVE_STATUSES,
            start_date__lte=period_end, end_date__gte=period_start,
        ).exists():
            raise ConflictError(
                "The nominated substitute has overlapping leave.",
                code="substitute_unavailable")
    case = LeaveCase.objects.create(
        leave_request=leave, case_type=case_type,
        requested_start=data.get("requested_start"),
        requested_end=data.get("requested_end"),
        actual_resumption_date=data.get("actual_resumption_date"),
        medical_evidence_ref=data.get("medical_evidence_ref", "").strip(),
        substitute_user_id=substitute_id,
        substitute_response="pending" if substitute_id else "",
        reason=data["reason"].strip(),
        status="awaiting_substitute" if substitute_id else "pending_unit_head")
    if substitute_id:
        case.assigned_user_id = substitute_id
        case.assigned_permission = "elm.leave.substitute_respond"
        case.save(update_fields=[
            "assigned_user_id", "assigned_permission", "updated_at",
        ])
        _notify(
            substitute_id, "leave.action_required",
            f"leave.case_substitute:{case.pk}:{case.updated_at.isoformat()}",
            f"Substitute response requested for leave action #{case.pk}",
            f"You have been nominated for responsibility coverage on leave "
            f"action #{case.pk}.")
    else:
        _assign_unit_head(case, profile)
    _audit(leave, actor.user_id, f"{case_type}_requested", case.reason, case)
    return case


@transaction.atomic
def decide_case(actor, case: LeaveCase, action: str, note: str = "") -> LeaveCase:
    _assert_assigned(actor, case)
    if case.status not in PENDING_STATUSES:
        raise ConflictError("This leave action is no longer pending.")
    leave = case.leave_request
    profile = _profile(leave.applicant_user_id)
    if case.status == "awaiting_substitute":
        _require(actor, "elm.leave.substitute_respond")
        if actor.user_id != case.substitute_user_id:
            raise PermissionDeniedError("Only the nominated substitute may respond.")
        if action not in {"accept", "decline"}:
            raise ConflictError("Substitute response must be accept or decline.")
        case.substitute_response = "accepted" if action == "accept" else "declined"
        if action == "accept":
            _assign_unit_head(case, profile)
        else:
            case.status = "applicant_action_required"
            case.assigned_user_id = leave.applicant_user_id
            case.assigned_permission = "elm.leave.apply"
            case.save(update_fields=[
                "status", "assigned_user_id", "assigned_permission",
                "substitute_response", "updated_at",
            ])
            _notify(
                leave.applicant_user_id, "leave.substitute_declined",
                f"leave.case_substitute_declined:{case.pk}",
                f"Substitute declined leave action #{case.pk}",
                "Nominate another substitute or withdraw the pending action.")
        _audit(leave, actor.user_id, f"substitute_{action}", note, case)
        return case
    if case.status == "pending_unit_head":
        _require(actor, "elm.leave.review")
        if not profile.organization_unit or (
            profile.organization_unit.unit_head_user_id != actor.user_id
        ):
            raise PermissionDeniedError("Only the applicant's Unit Head may review.")
        if leave.category in {"CL", "RH"}:
            if action not in {"approve", "reject"}:
                raise ConflictError("Unit Head must approve or reject.")
            final = True
        else:
            if action not in {"recommend", "not_recommended"}:
                raise ConflictError("Unit Head must record a recommendation.")
            final = False
    else:
        _require(actor, case.assigned_permission or "elm.leave.sanction")
        if action not in {"approve", "reject"}:
            raise ConflictError("The sanctioning authority must approve or reject.")
        final = True

    if not final:
        _audit(leave, actor.user_id, action, note, case)
        _assign_sanction(case, profile, leave.category)
        return case
    case.decided_at = timezone.now()
    case.status = "approved" if action == "approve" else "rejected"
    case.assigned_user_id = None
    case.assigned_permission = ""
    case.assigned_role = ""
    case.save(update_fields=[
        "decided_at", "status", "assigned_user_id", "assigned_permission",
        "assigned_role", "updated_at",
    ])
    if action == "approve":
        if case.case_type == "cancellation":
            amounts = _days_by_year(
                leave.category, leave.start_date, leave.end_date, leave.half_day)
            for year, amount in amounts.items():
                account = _account(
                    leave.applicant_user_id, leave.category, year,
                    profile.employee_type)
                account.used = max(ZERO, account.used - amount)
                _refresh_account(account)
                LeaveTransaction.objects.create(
                    user_id=leave.applicant_user_id, category=leave.category,
                    amount=amount, transaction_type="cancellation_credit",
                    reference_request=leave, reference_case=case,
                    performed_by_user_id=actor.user_id,
                    description="Approved pre-start leave cancellation")
            leave.status = "cancelled"
            leave.save(update_fields=["status", "updated_at"])
        elif case.case_type == "extension":
            amounts = _validate_period(
                leave.category, case.requested_start, case.requested_end, "none",
                profile.employee_type, leave.applicant_user_id, leave.pk)
            _charge(leave.applicant_user_id, profile.employee_type, leave.category,
                    amounts, leave, actor.user_id, "extension_debit")
        elif case.case_type == "resumption":
            actual = case.actual_resumption_date
            actual_end = actual
            effective_end = _effective_end(leave)
            if actual_end != effective_end:
                adjusted = _days_by_year(
                    leave.category, leave.start_date, actual_end, leave.half_day
                ) if actual_end >= leave.start_date else {}
                original = _days_by_year(
                    leave.category, leave.start_date, effective_end, leave.half_day)
                for year in set(original) | set(adjusted):
                    delta = original.get(year, ZERO) - adjusted.get(year, ZERO)
                    if delta:
                        account = _account(
                            leave.applicant_user_id, leave.category, year,
                            profile.employee_type)
                        if delta < ZERO and account.balance < -delta:
                            raise ConflictError(
                                f"Insufficient {leave.category} balance for the "
                                "late resumption adjustment.",
                                code="insufficient_leave_balance")
                        account.used = max(ZERO, account.used - delta)
                        _refresh_account(account)
                        LeaveTransaction.objects.create(
                            user_id=leave.applicant_user_id, category=leave.category,
                            amount=delta, transaction_type="resumption_adjustment",
                            reference_request=leave, reference_case=case,
                            performed_by_user_id=actor.user_id,
                            description="Resumption-period balance adjustment")
            leave.status = "completed"
            leave.save(update_fields=["status", "updated_at"])
        case.status = "completed" if case.case_type == "resumption" else "approved"
        case.save(update_fields=["status", "updated_at"])
    _audit(leave, actor.user_id, f"{case.case_type}_{action}", note, case)
    _notify(
        leave.applicant_user_id, "leave.case_decision",
        f"leave.case_decision:{case.pk}:{case.status}",
        f"Leave {case.case_type} request #{case.pk} {case.status}",
        f"Your {case.case_type} request for leave #{leave.pk} was {case.status}.")
    return case


@transaction.atomic
def withdraw_case(actor, case: LeaveCase) -> LeaveCase:
    _require(actor, "elm.leave.withdraw")
    if case.leave_request.applicant_user_id != actor.user_id:
        raise PermissionDeniedError("You may withdraw only your own leave action.")
    if case.status not in (*PENDING_STATUSES, "applicant_action_required"):
        raise ConflictError("Only a pending action can be withdrawn.")
    previous_assignee = case.assigned_user_id
    case.status = "withdrawn"
    case.assigned_user_id = None
    case.assigned_permission = ""
    case.assigned_role = ""
    case.save(update_fields=[
        "status", "assigned_user_id", "assigned_permission", "assigned_role",
        "updated_at",
    ])
    _audit(case.leave_request, actor.user_id, f"{case.case_type}_withdrawn",
           case=case)
    _notify(
        previous_assignee, "leave.case_withdrawn",
        f"leave.case_withdrawn:{case.pk}",
        f"Leave action #{case.pk} was withdrawn",
        f"The employee withdrew the {case.case_type} request.")
    return case


@transaction.atomic
def replace_case_substitute(actor, case: LeaveCase,
                            substitute_id: int) -> LeaveCase:
    _require(actor, "elm.leave.apply")
    if (case.leave_request.applicant_user_id != actor.user_id
            or case.status != "applicant_action_required"):
        raise ConflictError("This action is not awaiting a substitute replacement.")
    if substitute_id == actor.user_id:
        raise ConflictError("You cannot nominate yourself as substitute.",
                            code="invalid_substitute")
    _profile(substitute_id)
    start = case.requested_start or case.leave_request.start_date
    end = case.requested_end or _effective_end(case.leave_request)
    if LeaveRequest.objects.filter(
        applicant_user_id=substitute_id, status__in=ACTIVE_STATUSES,
        start_date__lte=end, end_date__gte=start,
    ).exists():
        raise ConflictError("The nominated substitute has overlapping leave.",
                            code="substitute_unavailable")
    case.substitute_user_id = substitute_id
    case.substitute_response = "pending"
    case.status = "awaiting_substitute"
    case.assigned_user_id = substitute_id
    case.assigned_permission = "elm.leave.substitute_respond"
    case.assigned_role = ""
    case.save(update_fields=[
        "substitute_user_id", "substitute_response", "status",
        "assigned_user_id", "assigned_permission", "assigned_role", "updated_at",
    ])
    _audit(case.leave_request, actor.user_id, "substitute_reassigned", case=case)
    _notify(
        substitute_id, "leave.action_required",
        f"leave.case_substitute:{case.pk}:{case.updated_at.isoformat()}",
        f"Substitute response requested for leave action #{case.pk}",
        f"You have been nominated for responsibility coverage on leave "
        f"action #{case.pk}.")
    return case


@transaction.atomic
def record_offline_leave(actor, data: dict) -> LeaveRequest:
    _require(actor, "elm.record.manage")
    profile = _profile(data["user_id"])
    category = data["category"]
    start, end = data["start_date"], data["end_date"]
    amounts = _validate_period(
        category, start, end, data.get("half_day", "none"),
        profile.employee_type, profile.user_id)
    leave = LeaveRequest.objects.create(
        applicant_user_id=profile.user_id, category=category,
        start_date=start, end_date=end, half_day=data.get("half_day", "none"),
        purpose=data["purpose"].strip(), status="approved",
        decided_at=timezone.now(), approved_days=sum(amounts.values(), ZERO))
    _charge(profile.user_id, profile.employee_type, category, amounts, leave,
            actor.user_id)
    _audit(leave, actor.user_id, "offline_sanction_recorded", data["purpose"])
    return leave


@transaction.atomic
def adjust_account(actor, user_id: int, category: str, year: int,
                   amount: Decimal, description: str) -> LeaveAccount:
    _require(actor, "elm.record.manage")
    if amount == ZERO:
        raise ConflictError("Adjustment amount cannot be zero.",
                            code="invalid_adjustment")
    profile = _profile(user_id)
    account = _account(user_id, category, year, profile.employee_type)
    if amount > ZERO:
        account.credited += amount
    else:
        if account.balance < -amount:
            raise ConflictError(
                "The adjustment would make the account balance negative.",
                code="insufficient_leave_balance")
        account.used += -amount
    _refresh_account(account)
    LeaveTransaction.objects.create(
        user_id=user_id, category=category, amount=amount,
        transaction_type="manual_adjustment", description=description.strip(),
        performed_by_user_id=actor.user_id)
    return account


@transaction.atomic
def _process_year_end_account(account_id: int, year: int) -> bool:
    account = LeaveAccount.objects.select_for_update().get(pk=account_id)
    if account.year_end_processed:
        return False
    profile = _profile(account.user_id)
    policy = LeavePolicy.objects.get(category=account.category, is_active=True)
    next_year = year + 1
    converted = ZERO
    if account.category == "VL" and profile.employee_type == "faculty":
        converted = account.balance / Decimal("2")
    _account(account.user_id, account.category, next_year, profile.employee_type)
    if converted:
        el_account = _account(
            account.user_id, "EL", next_year, profile.employee_type)
        el_account.credited += converted
        _refresh_account(el_account)
        LeaveTransaction.objects.create(
            user_id=account.user_id, category="EL", amount=converted,
            transaction_type="vl_to_el",
            description=f"{year} year-end conversion: 2 VL to 1 EL")
    if account.balance and not policy.carry_forward:
        lapsed = account.balance
        account.lapsed += lapsed
        _refresh_account(account)
        LeaveTransaction.objects.create(
            user_id=account.user_id, category=account.category,
            amount=-lapsed, transaction_type="year_end_lapse",
            description=f"{year} unused {account.category} lapsed")
    account.year_end_processed = True
    account.save(update_fields=["year_end_processed", "updated_at"])
    return True


@transaction.atomic
def process_year_end(actor, year: int) -> dict:
    _require(actor, "elm.leave.year_end")
    if year >= timezone.localdate().year:
        raise ConflictError("Year-end processing is available only for a completed year.",
                            code="invalid_year_end")
    results = {"processed": 0, "exceptions": []}
    account_ids = LeaveAccount.objects.filter(year=year).values_list("pk", flat=True)
    for account_id in account_ids:
        account = LeaveAccount.objects.get(pk=account_id)
        try:
            if _process_year_end_account(account_id, year):
                results["processed"] += 1
        except (ConflictError, LeavePolicy.DoesNotExist) as exc:
            results["exceptions"].append({
                "user_id": account.user_id,
                "category": account.category,
                "message": str(exc),
            })
    return results
