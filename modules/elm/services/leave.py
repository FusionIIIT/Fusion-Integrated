"""Transactional leave application, routing and decision services."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Q, Value, When
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.domain.rules import (
    LEAVE_TYPES,
    annual_entitlement,
    count_leave_days,
    overlaps,
)
from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    Holiday,
    LeaveAccount,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
    RequestEvent,
    VacationPeriod,
    WorkflowTask,
)
from modules.elm.services.notifications import enqueue as enqueue_notification

ACTIVE_REQUEST_STATUSES = (
    "substitute_pending", "applicant_action_required", "pending", "approved")


def _profile(user_id: int) -> EmployeeProfile:
    profile = EmployeeProfile.objects.filter(user_id=user_id, is_active=True).first()
    if profile is None:
        raise ConflictError(
            "Your ELM employee profile is not configured. Contact the Leave Administrator.",
            code="employee_profile_missing")
    if profile.unit_id is None:
        raise ConflictError(
            "Your ELM organizational unit is not configured.",
            code="employee_unit_missing")
    return profile


def _policy(year: int) -> LeavePolicy:
    policy = LeavePolicy.objects.filter(year=year).first()
    if policy is None:
        raise ConflictError(
            f"No leave policy is configured for {year}. Contact the Leave Administrator.",
            code="leave_policy_missing")
    return policy


@transaction.atomic
def account_for(user_id: int, category: str, year: int | None = None) -> LeaveAccount:
    if category not in LEAVE_TYPES:
        raise ConflictError("Unsupported leave category.", code="invalid_leave_category")
    profile = _profile(user_id)
    year = year or timezone.localdate().year
    policy = _policy(year)
    amounts = {
        "CL": policy.casual_days,
        "RH": policy.restricted_holiday_days,
        "SCL": policy.special_casual_days,
        "EL": policy.earned_days,
        "COL": policy.commuted_days,
        "VL": policy.vacation_days,
    }
    entitlement = min(
        amounts[category], annual_entitlement(category, profile.employee_kind))
    account, created = LeaveAccount.objects.get_or_create(
        user_id=user_id, category=category, year=year,
        defaults={"entitlement": entitlement, "balance": entitlement})
    if created and entitlement:
        LeaveTransaction.objects.create(
            account=account, amount=entitlement, transaction_type="annual_credit",
            reference=str(year), idempotency_key=f"entitlement:{user_id}:{category}:{year}")
    return account


def balances_for(user_id: int, year: int | None = None) -> list[LeaveAccount]:
    _profile(user_id)
    return [account_for(user_id, category, year) for category in LEAVE_TYPES]


def _published_holidays(year: int, *, kind: str | None = None) -> set[date]:
    qs = Holiday.objects.filter(
        calendar__year=year, calendar__status="published")
    if kind:
        qs = qs.filter(kind=kind)
    return set(qs.values_list("date", flat=True))


def _count_days(category: str, start: date, end: date, half_day_part: str) -> Decimal:
    if half_day_part not in ("", "first_half", "second_half"):
        raise ConflictError("Choose first half or second half for a half-day request.",
                            code="invalid_half_day")
    if half_day_part and category != "CL":
        raise ConflictError("Only Casual Leave supports half-day requests.",
                            code="invalid_half_day")
    if half_day_part and start != end:
        raise ConflictError("A half-day request must cover a single day.",
                            code="invalid_half_day")
    if start.year == end.year:
        return count_leave_days(
            start, end, category,
            holidays=_published_holidays(start.year, kind="closed"),
            half_day=bool(half_day_part))

    total = Decimal("0")
    year_start = start
    while year_start <= end:
        year_end = min(end, date(year_start.year, 12, 31))
        total += count_leave_days(
            year_start, year_end, category,
            holidays=_published_holidays(year_start.year, kind="closed"))
        year_start = date(year_start.year + 1, 1, 1)
    return total


def _days_by_year(category: str, start: date, end: date) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    year_start = start
    while year_start <= end:
        year_end = min(end, date(year_start.year, 12, 31))
        totals[year_start.year] = _count_days(category, year_start, year_end, "")
        year_start = date(year_start.year + 1, 1, 1)
    return totals


def _check_overlap(*, applicant_user_id: int, category: str, start: date,
                   end: date, half_day_part: str = "", exclude_id: int | None = None):
    qs = LeaveRequest.objects.filter(
        applicant_user_id=applicant_user_id,
        request_type__in=("leave", "extension"),
        status__in=ACTIVE_REQUEST_STATUSES,
        starts_on__lte=end, ends_on__gte=start,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    for existing in qs:
        if overlaps(start, end, existing.starts_on, existing.ends_on,
                    half_day_part=half_day_part or None,
                    other_half_day_part=existing.half_day_part or None,
                    category=category):
            raise ConflictError(
                f"The requested period overlaps leave request #{existing.pk}.",
                code="leave_overlap")


def _check_category_calendar(category: str, start: date, end: date):
    if category == "RH" and (
        start != end or start not in _published_holidays(start.year, kind="restricted")
    ):
        raise ConflictError(
            "RH must match one Restricted Holiday in the effective published calendar.",
            code="restricted_holiday_not_available")
    if category == "VL":
        covered = VacationPeriod.objects.filter(
            starts_on__lte=start, ends_on__gte=end).exists()
        if not covered:
            raise ConflictError(
                "VL must fall within a vacation period supplied by the Academic Calendar.",
                code="outside_vacation_period")


def _check_substitute(applicant_id: int, substitute_id: int | None,
                      start: date, end: date):
    if substitute_id is None:
        raise ConflictError("A substitute is required for this leave request.",
                            code="substitute_required")
    if substitute_id == applicant_id:
        raise ConflictError("You cannot nominate yourself as substitute.",
                            code="invalid_substitute")
    substitute = EmployeeProfile.objects.filter(
        user_id=substitute_id, is_active=True).first()
    if substitute is None:
        raise ConflictError("The nominated substitute is not an active employee.",
                            code="invalid_substitute")
    conflicting = LeaveRequest.objects.filter(
        applicant_user_id=substitute_id, request_type__in=("leave", "extension"),
        status__in=ACTIVE_REQUEST_STATUSES,
        starts_on__lte=end, ends_on__gte=start).exists()
    if conflicting:
        raise ConflictError(
            "The nominated substitute has pending or approved leave during this period.",
            code="substitute_unavailable")


def _event(request: LeaveRequest, actor_id: int | None, event: str,
           previous: str = "", note: str = ""):
    RequestEvent.objects.create(
        request=request, actor_user_id=actor_id, event=event,
        from_status=previous, to_status=request.status, note=note)


def _route_steps(request: LeaveRequest) -> list[tuple[str, int, bool]]:
    profile = _profile(request.applicant_user_id)
    if profile.is_director:
        return [("Director", profile.user_id, True)]
    unit_head = profile.unit.unit_head_user_id
    if unit_head == profile.user_id:
        raise ConflictError("An employee cannot approve their own leave.",
                            code="self_approval_route")
    if request.category in ("CL", "RH"):
        return [("unit_head", unit_head, True)]

    route = (ApprovalRoute.objects.filter(
        category=request.category, is_active=True,
    ).filter(Q(unit=profile.unit) | Q(unit__isnull=True))
        .filter(Q(designation=profile.designation) | Q(designation=""))
        .annotate(
            unit_priority=Case(
                When(unit=profile.unit, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            designation_priority=Case(
                When(designation=profile.designation, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        ).order_by("unit_priority", "designation_priority")
        .first())
    if route is None or not route.steps:
        raise ConflictError(
            f"No higher-sanction route is configured for {request.category}.",
            code="approval_route_missing")
    steps: list[tuple[str, int, bool]] = [("unit_head", unit_head, False)]
    for index, item in enumerate(route.steps):
        approver_id = item.get("user_id")
        role = item.get("role")
        if not isinstance(approver_id, int) or not role:
            raise ConflictError("The configured sanction route is invalid.",
                                code="approval_route_invalid")
        if approver_id == request.applicant_user_id:
            raise ConflictError("An employee cannot approve their own leave.",
                                code="self_approval_route")
        steps.append((str(role), approver_id, index == len(route.steps) - 1))
    return steps


def _start_approval(request: LeaveRequest, actor_id: int):
    steps = _route_steps(request)
    for sequence, (role, user_id, is_final) in enumerate(steps, start=1):
        WorkflowTask.objects.create(
            request=request, sequence=sequence, role=role,
            assigned_user_id=user_id, is_final=is_final,
            status="pending" if sequence == 1 else "waiting")
    request.status = "pending"
    request.save(update_fields=["status", "updated_at"])
    first = request.tasks.order_by("sequence").first()
    if first:
        RequestEvent.objects.create(
            request=request, actor_user_id=actor_id, event="task_assigned",
            to_status=request.status,
            note=f"Assigned to {first.role} ({first.assigned_user_id}).")
        enqueue_notification(
            topic="task_assigned",
            dedupe_key=f"task:{first.pk}:assigned",
            recipient_user_id=first.assigned_user_id,
            subject=f"ELM approval assigned: request {request.pk}",
            body=(f"Leave request {request.pk} is awaiting your decision "
                  f"in the {first.role} step."))


@transaction.atomic
def submit_leave(*, applicant_user_id: int, category: str, starts_on: date,
                 ends_on: date, purpose: str, half_day_part: str = "",
                 station_leave: bool = False, station_destination: str = "",
                 station_contact: str = "", medical_evidence: str = "",
                 substitute_user_id: int | None = None) -> LeaveRequest:
    profile = _profile(applicant_user_id)
    if category not in LEAVE_TYPES:
        raise ConflictError("Unsupported leave category.", code="invalid_leave_category")
    if not purpose.strip():
        raise ConflictError("A purpose/reason is required.", code="purpose_required")
    if ends_on < starts_on:
        raise ConflictError("The end date must be on or after the start date.",
                            code="invalid_date_range")
    if station_leave and not station_destination.strip():
        raise ConflictError("Station Leave requires a destination.",
                            code="station_destination_required")
    if half_day_part:
        days_by_year = {starts_on.year: _count_days(
            category, starts_on, ends_on, half_day_part)}
    else:
        days_by_year = _days_by_year(category, starts_on, ends_on)
    days = sum(days_by_year.values(), Decimal("0"))
    if days <= 0:
        raise ConflictError("The selected period contains no chargeable leave days.",
                            code="no_chargeable_days")
    _check_category_calendar(category, starts_on, ends_on)
    _check_overlap(applicant_user_id=applicant_user_id, category=category,
                   start=starts_on, end=ends_on, half_day_part=half_day_part)
    for year, year_days in days_by_year.items():
        account = account_for(applicant_user_id, category, year)
        if account.balance < year_days:
            raise ConflictError(
                f"Insufficient {category} balance ({account.balance} days available "
                f"for {year}).",
                code="insufficient_balance")

    requires_substitute = profile.requires_substitute
    if requires_substitute:
        _check_substitute(applicant_user_id, substitute_user_id, starts_on, ends_on)

    request = LeaveRequest.objects.create(
        applicant_user_id=applicant_user_id, category=category,
        request_type="leave",
        status="substitute_pending" if requires_substitute else "pending",
        starts_on=starts_on, ends_on=ends_on, half_day_part=half_day_part,
        requested_days=days, purpose=purpose.strip(),
        station_leave=station_leave, station_destination=station_destination.strip(),
        station_contact=station_contact.strip(), medical_evidence=medical_evidence.strip(),
        substitute_user_id=substitute_user_id if requires_substitute else None,
        substitute_response="pending" if requires_substitute else "",
        submitted_at=timezone.now())
    _event(request, applicant_user_id, "submitted")
    if not requires_substitute:
        _start_approval(request, applicant_user_id)
    return request


@transaction.atomic
def record_offline_leave(
    *, applicant_user_id: int, actor_id: int, category: str,
    starts_on: date, ends_on: date, purpose: str, offline_reference: str,
    offline_reason: str, offline_sanctioned_on: date,
) -> LeaveRequest:
    if category not in LEAVE_TYPES:
        raise ConflictError("Unsupported leave category.", code="invalid_leave_category")
    if ends_on < starts_on:
        raise ConflictError("The end date must be on or after the start date.",
                            code="invalid_date_range")
    if not purpose.strip() or not offline_reference.strip() or not offline_reason.strip():
        raise ConflictError(
            "Purpose, sanction reference, and ELM-unavailable reason are required.",
            code="offline_evidence_required")
    if offline_sanctioned_on > timezone.localdate():
        raise ConflictError("The offline sanction date cannot be in the future.",
                            code="invalid_offline_sanction_date")
    _profile(applicant_user_id)
    if LeaveRequest.objects.filter(
            applicant_user_id=applicant_user_id,
            offline_reference=offline_reference.strip()).exists():
        raise ConflictError(
            "This offline sanction reference has already been recorded for the employee.",
            code="duplicate_offline_reference")
    days_by_year = _days_by_year(category, starts_on, ends_on)
    total_days = sum(days_by_year.values(), Decimal("0"))
    if total_days <= 0:
        raise ConflictError("The selected period contains no chargeable leave days.",
                            code="no_chargeable_days")
    _check_category_calendar(category, starts_on, ends_on)
    _check_overlap(applicant_user_id=applicant_user_id, category=category,
                   start=starts_on, end=ends_on)

    accounts = {}
    for year, days in days_by_year.items():
        account = account_for(applicant_user_id, category, year)
        if account.balance < days:
            raise ConflictError(
                f"Insufficient {category} balance ({account.balance} days available "
                f"for {year}).",
                code="insufficient_balance")
        accounts[year] = (account, days)

    try:
        with transaction.atomic():
            request = LeaveRequest.objects.create(
                applicant_user_id=applicant_user_id,
                category=category,
                request_type="leave",
                status="approved",
                starts_on=starts_on,
                ends_on=ends_on,
                requested_days=total_days,
                purpose=purpose.strip(),
                offline_reference=offline_reference.strip(),
                offline_reason=offline_reason.strip(),
                offline_sanctioned_on=offline_sanctioned_on,
                submitted_at=timezone.now(),
                decided_at=timezone.now(),
                decision_note="Synchronized from an already-sanctioned offline record.",
            )
    except IntegrityError as exc:
        raise ConflictError(
            "This offline sanction reference has already been recorded for the employee.",
            code="duplicate_offline_reference") from exc

    for year, (account, days) in accounts.items():
        account = LeaveAccount.objects.select_for_update().get(pk=account.pk)
        if account.balance < days:
            raise ConflictError(
                f"The available {category} balance changed before recording for {year}.",
                code="insufficient_balance")
        account.balance = F("balance") - days
        account.used = F("used") + days
        account.save(update_fields=("balance", "used", "updated_at"))
        LeaveTransaction.objects.create(
            account=account, request=request, amount=-days,
            transaction_type="offline_entry",
            reference=request.offline_reference,
            idempotency_key=f"offline:{request.pk}:{year}",
            actor_user_id=actor_id)
    _event(
        request, actor_id, "offline_leave_synchronized",
        note=(f"Sanction reference {request.offline_reference}; "
              f"sanctioned {request.offline_sanctioned_on}; "
              f"reason: {request.offline_reason}"))
    return request


@transaction.atomic
def respond_to_substitute(*, request_id: int, actor_id: int, accept: bool):
    request = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, substitute_user_id=actor_id,
        status="substitute_pending").first()
    if request is None:
        raise NotFoundError("No pending substitute assignment was found.")
    previous = request.status
    request.substitute_response = "accepted" if accept else "declined"
    request.status = "pending" if accept else "applicant_action_required"
    request.save(update_fields=["substitute_response", "status", "updated_at"])
    _event(request, actor_id, "substitute_accepted" if accept else "substitute_declined",
           previous)
    if accept:
        _start_approval(request, actor_id)
    return request


@transaction.atomic
def replace_substitute(*, request_id: int, applicant_id: int,
                       substitute_user_id: int | None):
    request = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, applicant_user_id=applicant_id,
        status="applicant_action_required", substitute_response="declined").first()
    if request is None:
        raise NotFoundError("No declined substitute assignment can be replaced.")
    if request.events.filter(event="substitute_replaced").exists():
        raise ConflictError(
            "A replacement substitute has already been nominated for this request.",
            code="substitute_replacement_limit")
    _check_substitute(applicant_id, substitute_user_id,
                      request.starts_on, request.ends_on)
    request.substitute_user_id = substitute_user_id
    request.substitute_response = "pending"
    request.status = "substitute_pending"
    request.save(update_fields=[
        "substitute_user_id", "substitute_response", "status", "updated_at"])
    _event(request, applicant_id, "substitute_replaced")
    return request


def _debit(request: LeaveRequest, actor_id: int):
    for year, days in _days_by_year(
            request.category, request.starts_on, request.ends_on).items():
        account = account_for(request.applicant_user_id, request.category, year)
        account = LeaveAccount.objects.select_for_update().get(pk=account.pk)
        if account.balance < days:
            raise ConflictError(
                f"The available {request.category} balance changed before approval "
                f"for {year}.",
                code="insufficient_balance")
        account.balance = F("balance") - days
        account.used = F("used") + days
        account.save(update_fields=["balance", "used", "updated_at"])
        LeaveTransaction.objects.create(
            account=account, request=request, amount=-days,
            transaction_type="leave_debit",
            idempotency_key=f"request:{request.pk}:approval:{year}",
            actor_user_id=actor_id)


def _restore(request: LeaveRequest, actor_id: int):
    original = request.parent
    if original is None:
        raise ConflictError("The cancellation has no approved leave to restore.",
                            code="parent_request_missing")
    debits = original.transactions.filter(transaction_type="leave_debit")
    if not debits.exists():
        raise ConflictError("The original leave has no balance debit to restore.",
                            code="balance_transaction_missing")
    for debit in debits:
        account = LeaveAccount.objects.select_for_update().get(pk=debit.account_id)
        amount = abs(debit.amount)
        account.balance = F("balance") + amount
        account.used = F("used") - amount
        account.save(update_fields=["balance", "used", "updated_at"])
        LeaveTransaction.objects.create(
            account=account, request=request, amount=amount,
            transaction_type="cancellation_restore",
            idempotency_key=f"request:{request.pk}:cancellation:{account.year}",
            actor_user_id=actor_id)
    original.status = "cancelled"
    original.save(update_fields=["status", "updated_at"])
    _event(original, actor_id, "cancellation_approved", "approved")


def _apply_resumption(request: LeaveRequest, actor_id: int):
    original = request.parent
    if original is None or request.actual_resume_date is None:
        raise ConflictError("The resumption is missing its approved leave or return date.",
                            code="resumption_data_missing")
    early_days: dict[int, Decimal] = {}
    late_days: dict[int, Decimal] = {}
    if request.actual_resume_date < original.ends_on:
        early_days = _days_by_year(
            original.category, request.actual_resume_date + timedelta(days=1),
            original.ends_on)
    elif request.actual_resume_date > original.ends_on:
        late_days = _days_by_year(
            original.category, original.ends_on + timedelta(days=1),
            request.actual_resume_date)

    for year in early_days.keys() | late_days.keys():
        account = account_for(original.applicant_user_id, original.category, year)
        account = LeaveAccount.objects.select_for_update().get(pk=account.pk)
        restored = early_days.get(year, Decimal("0"))
        charged = late_days.get(year, Decimal("0"))
        if account.used < restored:
            raise ConflictError("Resumption adjustment exceeds the recorded leave usage.",
                                code="resumption_adjustment_invalid")
        if account.balance + restored < charged:
            raise ConflictError("Insufficient balance for the late resumption adjustment.",
                                code="insufficient_balance")
        amount = restored - charged
        account.balance = F("balance") + amount
        account.used = F("used") - amount
        account.save(update_fields=["balance", "used", "updated_at"])
        LeaveTransaction.objects.create(
            account=account, request=request, amount=amount,
            transaction_type="resumption_adjustment",
            idempotency_key=f"request:{request.pk}:resumption:{year}",
            actor_user_id=actor_id)
    _event(request, actor_id, "resumption_reviewed", "pending",
           f"Actual resumption date: {request.actual_resume_date}.")


@transaction.atomic
def decide_task(*, request_id: int, task_id: int, actor_id: int,
                action: str, note: str = ""):
    task = WorkflowTask.objects.select_for_update().filter(
        pk=task_id, request_id=request_id, assigned_user_id=actor_id,
        status="pending").first()
    if task is None:
        raise NotFoundError("No pending workflow task was found for this user.")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if action in ("recommend", "not_recommend") and task.is_final:
        raise ConflictError("A final authority must approve or reject this request.",
                            code="invalid_task_decision")
    if action in ("approve", "reject") and not task.is_final:
        raise ConflictError("This workflow step records a recommendation only.",
                            code="invalid_task_decision")
    if action not in ("approve", "reject", "recommend", "not_recommend"):
        raise ConflictError("Unsupported workflow decision.", code="invalid_task_decision")
    if action in ("reject", "not_recommend") and not note.strip():
        raise ConflictError("A reason is required for this decision.",
                            code="decision_reason_required")

    before = request.status
    task.status = {
        "approve": "approved", "reject": "rejected",
        "recommend": "recommended", "not_recommend": "not_recommended",
    }[action]
    task.acted_at = timezone.now()
    task.decision_note = note.strip()
    task.save(update_fields=["status", "acted_at", "decision_note", "updated_at"])

    if action == "reject":
        request.status = "rejected"
        request.decided_at = timezone.now()
        request.decision_note = note.strip()
        request.save(update_fields=["status", "decided_at", "decision_note", "updated_at"])
        _event(request, actor_id, "rejected", before, note)
        request.tasks.filter(status__in=("pending", "waiting")).update(status="cancelled")
    elif task.is_final:
        if request.request_type in ("leave", "extension"):
            _debit(request, actor_id)
        elif request.request_type == "cancellation":
            _restore(request, actor_id)
        elif request.request_type == "resumption":
            _apply_resumption(request, actor_id)
        request.status = "approved"
        request.decided_at = timezone.now()
        request.decision_note = note.strip()
        request.save(update_fields=["status", "decided_at", "decision_note", "updated_at"])
        _event(request, actor_id, "approved", before, note)
    else:
        next_task = request.tasks.filter(
            status="waiting").order_by("sequence").first()
        if next_task is None:
            raise ConflictError("The workflow has no remaining sanctioning authority.",
                                code="approval_route_incomplete")
        next_task.status = "pending"
        next_task.assigned_at = timezone.now()
        next_task.save(update_fields=["status", "assigned_at", "updated_at"])
        _event(request, actor_id, action, before, note)
        RequestEvent.objects.create(
            request=request, actor_user_id=actor_id, event="task_assigned",
            to_status=request.status,
            note=f"Assigned to {next_task.role} ({next_task.assigned_user_id}).")
        enqueue_notification(
            topic="task_assigned",
            dedupe_key=f"task:{next_task.pk}:assigned",
            recipient_user_id=next_task.assigned_user_id,
            subject=f"ELM approval assigned: request {request.pk}",
            body=(f"Leave request {request.pk} is awaiting your decision "
                  f"in the {next_task.role} step."))
    return request


@transaction.atomic
def withdraw_request(*, request_id: int, applicant_id: int):
    request = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, applicant_user_id=applicant_id,
        status__in=("substitute_pending", "applicant_action_required", "pending")).first()
    if request is None:
        raise NotFoundError("Only a pending request can be withdrawn.")
    old_status = request.status
    request.status = "withdrawn"
    request.save(update_fields=["status", "updated_at"])
    request.tasks.filter(status__in=("pending", "waiting")).update(status="cancelled")
    _event(request, applicant_id, "withdrawn", old_status)
    return request


@transaction.atomic
def request_cancellation(*, request_id: int, applicant_id: int, purpose: str):
    if not purpose.strip():
        raise ConflictError("A reason is required for cancellation.",
                            code="purpose_required")
    original = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, applicant_user_id=applicant_id, request_type="leave",
        status="approved").first()
    if original is None:
        raise NotFoundError("No approved leave request was found.")
    if timezone.localdate() >= original.starts_on:
        raise ConflictError("Approved leave can only be cancelled before it begins.",
                            code="cancellation_window_closed")
    cancellation = LeaveRequest.objects.create(
        applicant_user_id=applicant_id, category=original.category,
        request_type="cancellation", status="pending",
        starts_on=original.starts_on, ends_on=original.ends_on,
        requested_days=original.requested_days,
        purpose=purpose.strip(), parent=original, submitted_at=timezone.now())
    _event(cancellation, applicant_id, "cancellation_requested")
    _start_approval(cancellation, applicant_id)
    return cancellation


@transaction.atomic
def request_extension(*, request_id: int, applicant_id: int, ends_on: date,
                      purpose: str, substitute_user_id: int | None = None):
    if not purpose.strip():
        raise ConflictError("A purpose/reason is required.",
                            code="purpose_required")
    original = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, applicant_user_id=applicant_id, request_type="leave",
        category__in=("EL", "COL", "VL"), status="approved").first()
    if original is None:
        raise NotFoundError("No extendable EL, COL or VL request was found.")
    today = timezone.localdate()
    if not original.starts_on <= today <= original.ends_on:
        raise ConflictError("Extensions can only be requested while leave is ongoing.",
                            code="extension_window_closed")
    start = original.ends_on + timedelta(days=1)
    if ends_on < start:
        raise ConflictError("The extension end date must follow the original leave.",
                            code="invalid_extension_period")
    profile = _profile(applicant_id)
    if profile.requires_substitute:
        _check_substitute(applicant_id, substitute_user_id, start, ends_on)
    days_by_year = _days_by_year(original.category, start, ends_on)
    days = sum(days_by_year.values(), Decimal("0"))
    for year, year_days in days_by_year.items():
        account = account_for(applicant_id, original.category, year)
        if account.balance < year_days:
            raise ConflictError(
                f"Insufficient balance for the requested extension in {year}.",
                code="insufficient_balance")
    _check_category_calendar(original.category, start, ends_on)
    _check_overlap(applicant_user_id=applicant_id, category=original.category,
                   start=start, end=ends_on)
    extension = LeaveRequest.objects.create(
        applicant_user_id=applicant_id, category=original.category,
        request_type="extension",
        status="substitute_pending" if profile.requires_substitute else "pending",
        starts_on=start, ends_on=ends_on, requested_days=days,
        purpose=purpose.strip(), parent=original,
        substitute_user_id=substitute_user_id if profile.requires_substitute else None,
        substitute_response="pending" if profile.requires_substitute else "",
        submitted_at=timezone.now())
    _event(extension, applicant_id, "extension_requested")
    if not profile.requires_substitute:
        _start_approval(extension, applicant_id)
    return extension


@transaction.atomic
def request_resumption(*, request_id: int, applicant_id: int,
                       actual_resume_date: date, purpose: str):
    if not purpose.strip():
        raise ConflictError("A purpose/reason is required.",
                            code="purpose_required")
    original = LeaveRequest.objects.select_for_update().filter(
        pk=request_id, applicant_user_id=applicant_id, request_type="leave",
        category__in=("EL", "COL", "VL"), status="approved").first()
    if original is None:
        raise NotFoundError("No approved EL, COL or VL request was found.")
    if actual_resume_date < original.starts_on:
        raise ConflictError("The resumption date cannot precede the leave start.",
                            code="invalid_resumption_date")
    if actual_resume_date > timezone.localdate():
        raise ConflictError("The actual resumption date cannot be in the future.",
                            code="invalid_resumption_date")
    if original.follow_ups.filter(request_type="resumption").exists():
        raise ConflictError("A resumption has already been submitted.",
                            code="resumption_already_submitted")
    resumption = LeaveRequest.objects.create(
        applicant_user_id=applicant_id, category=original.category,
        request_type="resumption", status="pending",
        starts_on=original.starts_on, ends_on=original.ends_on,
        requested_days=Decimal("0"), purpose=purpose.strip(),
        actual_resume_date=actual_resume_date, parent=original,
        submitted_at=timezone.now())
    _event(resumption, applicant_id, "resumption_submitted")
    _start_approval(resumption, applicant_id)
    return resumption


def serialize_request(request: LeaveRequest) -> dict:
    tasks = [{
        "id": task.pk, "sequence": task.sequence, "role": task.role,
        "assigned_user_id": task.assigned_user_id, "is_final": task.is_final,
        "status": task.status, "decision_note": task.decision_note,
    } for task in request.tasks.all()]
    events = [{
        "event": event.event, "from_status": event.from_status,
        "to_status": event.to_status, "note": event.note,
        "created_at": event.created_at,
    } for event in request.events.all()]
    return {
        "id": request.pk, "applicant_user_id": request.applicant_user_id,
        "category": request.category, "request_type": request.request_type,
        "status": request.status, "starts_on": request.starts_on,
        "ends_on": request.ends_on, "half_day_part": request.half_day_part,
        "requested_days": request.requested_days, "purpose": request.purpose,
        "station_leave": request.station_leave,
        "station_destination": request.station_destination,
        "station_contact": request.station_contact,
        "medical_evidence": request.medical_evidence,
        "substitute_user_id": request.substitute_user_id,
        "substitute_response": request.substitute_response,
        "parent_id": request.parent_id,
        "actual_resume_date": request.actual_resume_date,
        "offline_reference": request.offline_reference,
        "submitted_at": request.submitted_at, "decided_at": request.decided_at,
        "decision_note": request.decision_note, "tasks": tasks, "events": events,
    }
