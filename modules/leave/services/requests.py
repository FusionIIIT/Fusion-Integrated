"""Transactional use-case services for leave requests and account entries."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from modules.leave.domain.state_machine import route_for, resumption_outcome, validate_cancellation, validate_withdrawal
from modules.leave.domain.eligibility import annual_entitlement
from modules.leave.domain.validation import validate_application
from modules.leave.models import (
    EmployeeProfile, HolidayCalendar, LeaveAccountEntry, LeaveAuditEvent,
    LeaveBalance, LeaveCategory, LeavePolicy, LeaveRequest, LeaveRouteConfiguration,
    LeaveSanction, LeaveSLAConfiguration, SubstituteResponse, VacationPeriod,
    WorkflowTask,
)
from modules.leave.services.notifications import enqueue as enqueue_notification, enqueue_task


class LeaveRuleViolation(ValueError):
    """A request conflicts with an ELM rule or current configuration."""


def _effective_calendar(year: int):
    return HolidayCalendar.objects.filter(year=year, state=HolidayCalendar.State.PUBLISHED).order_by("-revision").first()


def _calendar_dates(year: int):
    calendar = _effective_calendar(year)
    if not calendar:
        return (), ()
    holidays, rh_dates = [], []
    for item in calendar.holidays:
        try:
            day = date.fromisoformat(item["date"])
        except (KeyError, TypeError, ValueError):
            continue
        holidays.append(day)
        if item.get("restricted_holiday") or item.get("type") == "RH":
            rh_dates.append(day)
    return tuple(holidays), tuple(rh_dates)


def _duration_by_year(request: LeaveRequest) -> dict[int, Decimal]:
    grouped = {}
    for year in range(request.start_date.year, request.end_date.year + 1):
        start, end = max(request.start_date, date(year, 1, 1)), min(request.end_date, date(year, 12, 31))
        holidays, rh_dates = _calendar_dates(year)
        grouped[year] = calculate_duration(request.category_id, start, end,
                                            cl_portion=request.cl_portion,
                                            holidays=holidays, rh_dates=rh_dates)
    return grouped


def _current_policy():
    policy = LeavePolicy.objects.filter(policy_key="current").first()
    if not policy:
        raise LeaveRuleViolation("Leave policy has not been configured")
    return policy


def _post_entry(*, employee_id, category, year, amount, kind, source_key,
                request=None, actor_user_id=None, explanation=""):
    entry, created = LeaveAccountEntry.objects.get_or_create(
        source_key=source_key,
        defaults={"employee_id": employee_id, "category": category, "year": year,
                  "amount": amount, "kind": kind, "request": request,
                  "actor_user_id": actor_user_id, "explanation": explanation},
    )
    if created:
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=employee_id, category=category, year=year,
            defaults={"available": Decimal("0")},
        )
        balance.available += amount
        if kind == LeaveAccountEntry.Kind.ENTITLEMENT:
            balance.entitlement += amount
        if kind == LeaveAccountEntry.Kind.CARRY_FORWARD and amount > 0:
            balance.carried_over += amount
        fields = ["available", "updated_at"]
        if kind == LeaveAccountEntry.Kind.ENTITLEMENT:
            fields.append("entitlement")
        if kind == LeaveAccountEntry.Kind.CARRY_FORWARD and amount > 0:
            fields.append("carried_over")
        balance.save(update_fields=fields)
    return entry


def _validate_request(request: LeaveRequest, employee: EmployeeProfile):
    policy = _current_policy()
    balances = []
    for year in range(request.start_date.year, request.end_date.year + 1):
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=employee.user_id, category=request.category, year=year)
        key = f"entitlement:{employee.user_id}:{request.category_id}:{year}"
        credit = annual_entitlement(request.category_id, employee.kind, policy)
        if credit and not LeaveAccountEntry.objects.filter(source_key=key).exists():
            _post_entry(employee_id=employee.user_id, category=request.category, year=year,
                        amount=credit, kind=LeaveAccountEntry.Kind.ENTITLEMENT,
                        source_key=key, explanation="Annual leave entitlement")
            balance.refresh_from_db()
        balances.append(balance)
    available = sum((balance.available for balance in balances), Decimal("0"))
    holidays, rh_dates = [], []
    for year in range(request.start_date.year, request.end_date.year + 1):
        h, r = _calendar_dates(year)
        holidays.extend(h)
        rh_dates.extend(r)
    overlaps = LeaveRequest.objects.filter(
        employee_id=employee.user_id,
        status__in=[LeaveRequest.Status.AWAITING_SUBSTITUTE, LeaveRequest.Status.APPLICANT_ACTION,
                    LeaveRequest.Status.PENDING_UNIT_HEAD, LeaveRequest.Status.PENDING_ESTABLISHMENT,
                    LeaveRequest.Status.PENDING_AUTHORITY, LeaveRequest.Status.APPROVED],
        start_date__lte=request.end_date, end_date__gte=request.start_date,
    ).exclude(pk=request.pk).values_list("start_date", "end_date", "category__code", "cl_portion")
    vacations = VacationPeriod.objects.filter(start_date__lte=request.start_date, end_date__gte=request.end_date).values_list("start_date", "end_date")
    result = validate_application(
        category=request.category_id, start=request.start_date, end=request.end_date,
        employee_kind=employee.kind, cl_portion=request.cl_portion,
        station_leave=request.station_leave, station_destination=request.station_destination,
        station_departure_at=request.station_departure_at, station_return_at=request.station_return_at,
        holidays=holidays, rh_dates=rh_dates, available=available,
        overlapping=overlaps,
        medical_evidence_ref=request.medical_evidence_ref,
        medical_required=policy.col_medical_evidence_required,
        vacation_periods=vacations,
    )
    if not result.is_valid:
        raise LeaveRuleViolation("; ".join(result.errors))
    by_year = _duration_by_year(request)
    for balance in balances:
        required = by_year.get(balance.year, Decimal("0"))
        if required > balance.available:
            raise LeaveRuleViolation(
                f"Insufficient {request.category_id} balance for {balance.year}: "
                f"{balance.available} available, {required} requested"
            )
    # SCL admissibility is an authority judgment. The service deliberately does
    # not try to infer it from employee kind or encode purpose categories.
    request.duration_days = sum(by_year.values(), Decimal("0"))
    return request


@transaction.atomic
def submit_request(request_id: int, actor_user_id: int):
    request = LeaveRequest.objects.select_for_update().select_related("category").get(pk=request_id)
    if request.employee_id != actor_user_id or request.status != LeaveRequest.Status.DRAFT:
        raise LeaveRuleViolation("Only the employee may submit their own draft")
    employee = EmployeeProfile.objects.get(user_id=actor_user_id, active=True)
    request = _validate_request(request, employee)
    config = _route_configuration(request, employee)
    if config and config.requires_substitute and not request.substitute_user_id:
        raise LeaveRuleViolation("A substitute is required for this leave route")
    request.submitted_at = timezone.now()
    if request.substitute_user_id:
        substitute = EmployeeProfile.objects.filter(user_id=request.substitute_user_id, active=True).first()
        if not substitute or substitute.user_id == employee.user_id:
            raise LeaveRuleViolation("Substitute must be another active employee")
        if LeaveRequest.objects.filter(
            employee_id=substitute.user_id,
            status__in=[LeaveRequest.Status.AWAITING_SUBSTITUTE, LeaveRequest.Status.APPLICANT_ACTION,
                        LeaveRequest.Status.PENDING_UNIT_HEAD, LeaveRequest.Status.PENDING_ESTABLISHMENT,
                        LeaveRequest.Status.PENDING_AUTHORITY, LeaveRequest.Status.APPROVED],
            start_date__lte=request.end_date, end_date__gte=request.start_date,
        ).exists():
            raise LeaveRuleViolation("Substitute has overlapping pending or approved leave")
        request.status = LeaveRequest.Status.AWAITING_SUBSTITUTE
        _create_substitute_task(request, substitute.user_id)
    else:
        request.status = LeaveRequest.Status.PENDING_UNIT_HEAD
        first_task = _create_route_tasks(request, employee)
        request.status = _status_for_role(first_task.role)
    request.save()
    LeaveAuditEvent.objects.create(request=request, action="submitted", from_status="draft", to_status=request.status,
                                   actor_user_id=actor_user_id)
    return request


def _count_request_days(request):
    return sum(_duration_by_year(request).values(), Decimal("0"))


def _create_route_tasks(request: LeaveRequest, employee: EmployeeProfile):
    cfg = _route_configuration(request, employee)
    if employee.is_director:
        route = route_for(category=request.category_id, is_director=True,
                          establishment_role=None, final_authority_role=None)
    elif request.category_id in {"CL", "RH"}:
        route = route_for(category=request.category_id, is_director=False,
                          establishment_role=None, final_authority_role="unit_head")
    else:
        if not cfg:
            raise LeaveRuleViolation("No current sanction route is configured for this employee and leave category")
        route = route_for(category=request.category_id, is_director=False,
                          establishment_role=cfg.establishment_role or None,
                          final_authority_role=cfg.final_authority_role)
    created = []
    start_sequence = (request.tasks.order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1
    created = []
    for index, step in enumerate(route):
        sequence = start_sequence + index
        if step.role == "unit_head":
            assigned = employee.unit_head_user_id
        elif step.role == "director":
            assigned = employee.user_id
        elif step.role == "establishment":
            assigned = cfg.establishment_user_id if cfg else None
        else:
            assigned = cfg.final_authority_user_id if cfg else None
        if assigned is None:
            raise LeaveRuleViolation(f"No user is assigned to the {step.role.replace('_', ' ')} workflow step")
        task = WorkflowTask.objects.create(
            request=request, sequence=sequence, role=step.role,
            decision_kind=step.decision_kind, assigned_user_id=assigned,
            state=WorkflowTask.State.PENDING if index == 0 else WorkflowTask.State.QUEUED,
            activated_at=timezone.now() if index == 0 else None,
            due_at=_task_due_at(step.role) if index == 0 else None,
        )
        created.append(task)
    if not created:
        raise LeaveRuleViolation("No workflow task was created")
    enqueue_task(created[0])
    return created[0]


def _task_due_at(role: str):
    config, _ = LeaveSLAConfiguration.objects.get_or_create(role=role)
    hours = config.escalate_after_hours if config else 72
    return timezone.now() + timedelta(hours=hours)


def _create_substitute_task(request: LeaveRequest, substitute_user_id: int):
    sequence = (request.tasks.order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1
    task = WorkflowTask.objects.create(
        request=request, sequence=sequence, role="substitute", decision_kind="forward",
        assigned_user_id=substitute_user_id, state=WorkflowTask.State.PENDING,
        activated_at=timezone.now(),
        due_at=_task_due_at("substitute"),
    )
    enqueue_task(task)
    return task


def _route_configuration(request: LeaveRequest, employee: EmployeeProfile):
    return LeaveRouteConfiguration.objects.filter(
        category=request.category, employee_kind=employee.kind, active=True,
    ).filter(Q(designation="") | Q(designation=employee.designation)).filter(
        Q(unit_code="") | Q(unit_code=employee.unit_code)
    ).order_by("-unit_code", "-designation").first()


@transaction.atomic
def respond_to_substitute(request_id: int, actor_user_id: int, *, accepted: bool):
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if request.status != LeaveRequest.Status.AWAITING_SUBSTITUTE or request.substitute_user_id != actor_user_id:
        raise LeaveRuleViolation("This substitute request is no longer pending for you")
    SubstituteResponse.objects.create(request=request, substitute_user_id=actor_user_id,
                                      decision=SubstituteResponse.Decision.ACCEPTED if accepted else SubstituteResponse.Decision.DECLINED)
    old = request.status
    request.tasks.filter(role="substitute", state=WorkflowTask.State.PENDING,
                         assigned_user_id=actor_user_id).update(state=WorkflowTask.State.COMPLETED)
    if accepted:
        first_task = _create_route_tasks(request, EmployeeProfile.objects.get(user_id=request.employee_id))
        request.status = _status_for_role(first_task.role)
    else:
        request.status = LeaveRequest.Status.APPLICANT_ACTION
    request.save(update_fields=["status", "updated_at"])
    LeaveAuditEvent.objects.create(request=request, action="substitute_accepted" if accepted else "substitute_declined",
                                   from_status=old, to_status=request.status, actor_user_id=actor_user_id)
    return request


@transaction.atomic
def replace_declined_substitute(request_id: int, actor_user_id: int, substitute_user_id: int):
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if request.employee_id != actor_user_id or request.status != LeaveRequest.Status.APPLICANT_ACTION:
        raise LeaveRuleViolation("Only the applicant may replace a declined substitute")
    declined = request.substitute_responses.filter(decision=SubstituteResponse.Decision.DECLINED).count()
    if declined != 1:
        raise LeaveRuleViolation("One substitute replacement is allowed after the initial decline")
    substitute = EmployeeProfile.objects.filter(user_id=substitute_user_id, active=True).first()
    if not substitute or substitute.user_id == actor_user_id:
        raise LeaveRuleViolation("Replacement must be another active employee")
    overlap = LeaveRequest.objects.filter(
        employee_id=substitute_user_id,
        status__in=[LeaveRequest.Status.AWAITING_SUBSTITUTE, LeaveRequest.Status.APPLICANT_ACTION,
                    LeaveRequest.Status.PENDING_UNIT_HEAD, LeaveRequest.Status.PENDING_ESTABLISHMENT,
                    LeaveRequest.Status.PENDING_AUTHORITY, LeaveRequest.Status.APPROVED],
        start_date__lte=request.end_date, end_date__gte=request.start_date,
    ).exists()
    if overlap:
        raise LeaveRuleViolation("Replacement substitute has overlapping pending or approved leave")
    request.substitute_user_id = substitute_user_id
    request.status = LeaveRequest.Status.AWAITING_SUBSTITUTE
    request.save(update_fields=["substitute_user_id", "status", "updated_at"])
    _create_substitute_task(request, substitute_user_id)
    LeaveAuditEvent.objects.create(request=request, action="substitute_replaced",
                                   from_status=LeaveRequest.Status.APPLICANT_ACTION,
                                   to_status=request.status, actor_user_id=actor_user_id,
                                   details={"substitute_user_id": substitute_user_id})
    return request


@transaction.atomic
def withdraw_request(request_id: int, actor_user_id: int):
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if request.employee_id != actor_user_id:
        raise LeaveRuleViolation("Only the applicant may withdraw this request")
    validate_withdrawal(request.status)
    old = request.status
    request.status = LeaveRequest.Status.WITHDRAWN
    request.save(update_fields=["status", "updated_at"])
    request.tasks.filter(state=WorkflowTask.State.PENDING).update(state=WorkflowTask.State.CANCELLED)
    for task in request.tasks.filter(assigned_user_id__isnull=False):
        enqueue_notification(
            recipient_user_id=task.assigned_user_id,
            dedupe_key=f"request:{request.pk}:withdrawn:task:{task.pk}",
            topic="request.withdrawn", subject="ELM request withdrawn",
            body=f"Leave request #{request.pk} was withdrawn by the applicant.",
            payload={"request_id": request.pk, "task_id": task.pk},
        )
    LeaveAuditEvent.objects.create(request=request, action="withdrawn", from_status=old,
                                   to_status=request.status, actor_user_id=actor_user_id)
    return request


@transaction.atomic
def decide_task(task_id: int, actor_user_id: int, *, decision: str, notes: str = ""):
    task = WorkflowTask.objects.select_for_update().select_related("request", "request__category").get(pk=task_id)
    if task.state != WorkflowTask.State.PENDING:
        raise LeaveRuleViolation("This workflow task is no longer pending")
    if task.assigned_user_id and task.assigned_user_id != actor_user_id:
        raise LeaveRuleViolation("This task is assigned to another user")
    request = LeaveRequest.objects.select_for_update().get(pk=task.request_id)
    allowed = {"final": {"approved", "rejected"},
               "recommendation": {"recommended", "not_recommended"},
               "forward": {"forwarded"}}
    if decision not in allowed[task.decision_kind]:
        raise LeaveRuleViolation("Decision is not valid for this workflow step")
    LeaveSanction.objects.create(task=task, actor_user_id=actor_user_id, decision=decision, notes=notes)
    task.state = WorkflowTask.State.COMPLETED
    task.save(update_fields=["state"])
    old = request.status
    if task.decision_kind == "final":
        if decision == "approved":
            _apply_final_approval(request, actor_user_id)
            request.status = (LeaveRequest.Status.COMPLETED
                              if request.request_type == LeaveRequest.Type.RESUMPTION
                              else LeaveRequest.Status.APPROVED)
        else:
            request.status = LeaveRequest.Status.REJECTED
        request.decided_at = timezone.now()
    else:
        next_task = request.tasks.filter(state=WorkflowTask.State.QUEUED).order_by("sequence").first()
        if not next_task:
            raise LeaveRuleViolation("No next authority is configured for this workflow")
        next_task.state = WorkflowTask.State.PENDING
        next_task.due_at = _task_due_at(next_task.role)
        next_task.activated_at = timezone.now()
        next_task.save(update_fields=["state", "due_at", "activated_at"])
        enqueue_task(next_task)
        request.status = _status_for_role(next_task.role)
    request.save(update_fields=["status", "decided_at", "updated_at"])
    LeaveAuditEvent.objects.create(request=request, action=decision, from_status=old,
                                   to_status=request.status, actor_user_id=actor_user_id,
                                   details={"task_id": task.id, "notes": notes})
    if task.decision_kind == "final":
        from modules.leave.services.notifications import enqueue_decision
        enqueue_decision(request, decision=decision)
    return request


def _status_for_role(role: str) -> str:
    return {"unit_head": LeaveRequest.Status.PENDING_UNIT_HEAD,
            "establishment": LeaveRequest.Status.PENDING_ESTABLISHMENT}.get(role, LeaveRequest.Status.PENDING_AUTHORITY)


def _approve_leave(request, actor_user_id):
    if request.request_type != LeaveRequest.Type.NEW:
        return
    for year, days in _duration_by_year(request).items():
        _post_entry(employee_id=request.employee_id, category=request.category,
                    year=year, amount=-days, kind=LeaveAccountEntry.Kind.LEAVE_USED,
                    source_key=f"request:{request.pk}:approved:{year}", request=request,
                    actor_user_id=actor_user_id, explanation="Approved leave")


def _apply_final_approval(request, actor_user_id):
    if request.request_type == LeaveRequest.Type.NEW:
        _approve_leave(request, actor_user_id)
    elif request.request_type == LeaveRequest.Type.CANCELLATION:
        original = LeaveRequest.objects.select_for_update().get(pk=request.parent_request_id)
        original.status = LeaveRequest.Status.CANCELLED
        original.save(update_fields=["status", "updated_at"])
        for debit in original.account_entries.filter(kind=LeaveAccountEntry.Kind.LEAVE_USED):
            _post_entry(employee_id=original.employee_id, category=original.category,
                        year=debit.year, amount=-debit.amount,
                        kind=LeaveAccountEntry.Kind.CANCELLATION_REVERSAL,
                        source_key=f"request:{request.pk}:cancellation-reversal:{debit.year}", request=original,
                        actor_user_id=actor_user_id, explanation="Approved leave cancellation")
    elif request.request_type == LeaveRequest.Type.EXTENSION:
        for year, days in _duration_by_year(request).items():
            _post_entry(employee_id=request.employee_id, category=request.category,
                        year=year, amount=-days, kind=LeaveAccountEntry.Kind.LEAVE_USED,
                        source_key=f"request:{request.pk}:extension-approved:{year}", request=request,
                        actor_user_id=actor_user_id, explanation="Approved extension period")
    elif request.request_type == LeaveRequest.Type.RESUMPTION:
        original = LeaveRequest.objects.select_for_update().get(pk=request.parent_request_id)
        outcome = resumption_outcome(approved_end_date=original.end_date,
                                     actual_resume_date=request.actual_resume_date)
        approved_by_year = _duration_by_year(original)
        actual_end = request.actual_resume_date.fromordinal(request.actual_resume_date.toordinal() - 1)
        actual_by_year = {}
        if actual_end >= original.start_date:
            for year in range(original.start_date.year, actual_end.year + 1):
                first, last = max(original.start_date, date(year, 1, 1)), min(actual_end, date(year, 12, 31))
                actual_by_year[year] = Decimal((last - first).days + 1)
        adjustments = {}
        if outcome != "normal":
            for year in approved_by_year.keys() | actual_by_year.keys():
                amount = approved_by_year.get(year, Decimal("0")) - actual_by_year.get(year, Decimal("0"))
                if amount:
                    _post_entry(employee_id=original.employee_id, category=original.category,
                                year=year, amount=amount,
                                kind=LeaveAccountEntry.Kind.RESUMPTION_ADJUSTMENT,
                                source_key=f"request:{request.pk}:resumption-adjustment:{year}", request=original,
                                actor_user_id=actor_user_id, explanation="Reviewed early/late resumption")
                    adjustments[year] = str(amount)
        LeaveAuditEvent.objects.create(request=request, action=f"resumption_{outcome}",
                                       from_status=request.status, to_status=request.status,
                                       actor_user_id=actor_user_id,
                                       details={"approved_days": {str(k): str(v) for k, v in approved_by_year.items()},
                                                "actual_days": {str(k): str(v) for k, v in actual_by_year.items()},
                                                "balance_adjustment": adjustments})


@transaction.atomic
def request_cancellation(request_id: int, actor_user_id: int):
    original = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if original.employee_id != actor_user_id:
        raise LeaveRuleViolation("Only the employee may request cancellation")
    validate_cancellation(status=original.status, start_date=original.start_date, today=timezone.localdate())
    cancellation = LeaveRequest.objects.create(
        employee_id=actor_user_id, category=original.category, request_type=LeaveRequest.Type.CANCELLATION,
        parent_request=original, start_date=original.start_date, end_date=original.end_date,
        duration_days=original.duration_days, reason="Cancellation requested",
        status=LeaveRequest.Status.PENDING_UNIT_HEAD,
    )
    employee = EmployeeProfile.objects.get(user_id=actor_user_id)
    first_task = _create_route_tasks(cancellation, employee)
    cancellation.status = _status_for_role(first_task.role)
    cancellation.save(update_fields=["status", "updated_at"])
    LeaveAuditEvent.objects.create(request=cancellation, action="cancellation_requested",
                                   from_status="approved", to_status=cancellation.status,
                                   actor_user_id=actor_user_id)
    return cancellation


@transaction.atomic
def request_extension(request_id: int, actor_user_id: int, *, new_end_date: date,
                      reason: str, substitute_user_id: int | None = None):
    from datetime import timedelta
    from modules.leave.domain.state_machine import validate_extension
    original = LeaveRequest.objects.select_for_update().select_related("category").get(pk=request_id)
    validate_extension(category=original.category_id, status=original.status,
                       start_date=original.start_date, end_date=original.end_date,
                       new_end_date=new_end_date, today=timezone.localdate())
    if original.employee_id != actor_user_id:
        raise LeaveRuleViolation("Only the employee may request an extension")
    period_start = original.end_date + timedelta(days=1)
    extension = LeaveRequest.objects.create(
        employee_id=actor_user_id, category=original.category, request_type=LeaveRequest.Type.EXTENSION,
        parent_request=original, start_date=period_start, end_date=new_end_date,
        duration_days=Decimal((new_end_date - original.end_date).days), reason=reason,
        substitute_user_id=substitute_user_id,
        status=LeaveRequest.Status.AWAITING_SUBSTITUTE if substitute_user_id else LeaveRequest.Status.PENDING_UNIT_HEAD,
    )
    employee = EmployeeProfile.objects.get(user_id=actor_user_id, active=True)
    _validate_request(extension, employee)
    config = _route_configuration(extension, employee)
    if config and config.requires_substitute and not substitute_user_id:
        raise LeaveRuleViolation("A substitute is required for this extension route")
    if substitute_user_id:
        substitute = EmployeeProfile.objects.filter(user_id=substitute_user_id, active=True).first()
        if not substitute or substitute.user_id == actor_user_id:
            raise LeaveRuleViolation("Substitute must be another active employee")
        if LeaveRequest.objects.filter(
            employee_id=substitute_user_id,
            status__in=[LeaveRequest.Status.AWAITING_SUBSTITUTE, LeaveRequest.Status.APPLICANT_ACTION,
                        LeaveRequest.Status.PENDING_UNIT_HEAD, LeaveRequest.Status.PENDING_ESTABLISHMENT,
                        LeaveRequest.Status.PENDING_AUTHORITY, LeaveRequest.Status.APPROVED],
            start_date__lte=extension.end_date, end_date__gte=extension.start_date,
        ).exists():
            raise LeaveRuleViolation("Substitute has overlapping pending or approved leave")
    if not substitute_user_id:
        first_task = _create_route_tasks(extension, employee)
        extension.status = _status_for_role(first_task.role)
        extension.save(update_fields=["status", "updated_at"])
    else:
        _create_substitute_task(extension, substitute_user_id)
    LeaveAuditEvent.objects.create(request=extension, action="extension_requested",
                                   from_status="approved", to_status=extension.status,
                                   actor_user_id=actor_user_id)
    return extension


@transaction.atomic
def submit_resumption(request_id: int, actor_user_id: int, *, actual_resume_date: date,
                      reason: str):
    original = LeaveRequest.objects.select_for_update().select_related("category").get(pk=request_id)
    if original.employee_id != actor_user_id or original.category_id not in {"EL", "COL", "VL"}:
        raise LeaveRuleViolation("Resumption is available to the employee for approved EL, COL, or VL only")
    if original.status != LeaveRequest.Status.APPROVED:
        raise LeaveRuleViolation("Only approved leave can be resumed")
    if actual_resume_date > timezone.localdate():
        raise LeaveRuleViolation("Actual resumption date cannot be in the future")
    if actual_resume_date < original.start_date:
        raise LeaveRuleViolation("Actual resumption cannot precede leave start")
    # The reviewer is the same final authority resolved for the original request.
    final = original.tasks.order_by("-sequence").first()
    if not final:
        raise LeaveRuleViolation("The original sanction route is unavailable")
    followup = LeaveRequest.objects.create(
        employee_id=actor_user_id, category=original.category, request_type=LeaveRequest.Type.RESUMPTION,
        parent_request=original, start_date=original.start_date, end_date=original.end_date,
        duration_days=original.duration_days, actual_resume_date=actual_resume_date,
        reason=reason, status=LeaveRequest.Status.PENDING_AUTHORITY,
    )
    task = WorkflowTask.objects.create(request=followup, sequence=1, role=final.role,
                                       decision_kind="final", assigned_user_id=final.assigned_user_id)
    enqueue_task(task)
    LeaveAuditEvent.objects.create(request=followup, action="resumption_submitted",
                                   from_status="approved", to_status=followup.status,
                                   actor_user_id=actor_user_id)
    return followup


@transaction.atomic
def record_offline_sanctioned_leave(*, employee_id: int, category_code: str,
                                    start_date: date, end_date: date, reason: str,
                                    sanction_reference: str, evidence_reference: str,
                                    actor_user_id: int):
    """Synchronize an already-sanctioned offline leave without a second approval."""
    from modules.leave.domain.validation import calculate_duration
    employee = EmployeeProfile.objects.get(user_id=employee_id, active=True)
    category = LeaveCategory.objects.get(pk=category_code)
    req = LeaveRequest(employee_id=employee_id, category=category,
                       request_type=LeaveRequest.Type.OFFLINE, start_date=start_date,
                       end_date=end_date, duration_days=Decimal("0"), reason=reason,
                       offline_sanction_ref=sanction_reference,
                       offline_evidence_ref=evidence_reference)
    if not sanction_reference.strip() or not evidence_reference.strip():
        raise LeaveRuleViolation("Offline entry requires sanction reference and evidence")
    req = _validate_request(req, employee)
    req.duration_days = _count_request_days(req)
    req.status = LeaveRequest.Status.APPROVED
    req.submitted_at = req.decided_at = timezone.now()
    req.save()
    for year, days in _duration_by_year(req).items():
        _post_entry(employee_id=employee_id, category=category, year=year,
                    amount=-days, kind=LeaveAccountEntry.Kind.OFFLINE_ADJUSTMENT,
                    source_key=f"request:{req.pk}:offline-record:{year}", request=req,
                    actor_user_id=actor_user_id,
                    explanation=f"Offline sanction {sanction_reference}")
    LeaveAuditEvent.objects.create(request=req, action="offline_sanction_recorded",
                                   from_status="", to_status=req.status,
                                   actor_user_id=actor_user_id,
                                   details={"sanction_reference": sanction_reference,
                                            "evidence_reference": evidence_reference})
    return req


@transaction.atomic
def record_account_adjustment(*, employee_id: int, category: LeaveCategory, year: int,
                              amount: Decimal, reference: str, explanation: str,
                              actor_user_id: int):
    if not reference.strip() or not explanation.strip() or amount == 0:
        raise LeaveRuleViolation("An adjustment needs a non-zero amount, reference, and explanation")
    if not EmployeeProfile.objects.filter(user_id=employee_id, active=True).exists():
        raise LeaveRuleViolation("Employee is not active in the ELM projection")
    return _post_entry(employee_id=employee_id, category=category, year=year,
                       amount=amount, kind=LeaveAccountEntry.Kind.OFFLINE_ADJUSTMENT,
                       source_key=f"admin-adjustment:{reference}", actor_user_id=actor_user_id,
                       explanation=explanation)
