"""Transactional ELM workflows. IAM remains the source of employee identity."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain import policy, workflow
from modules.elm.models import (
    AdminAuditEvent,
    ApprovalRoute,
    CalendarEntry,
    ELMNotification,
    EmployeeContext,
    HolidayCalendar,
    LeaveAccount,
    LeaveCategory,
    LeaveEvent,
    LeaveRequest,
    LeaveReservation,
    LeaveTransaction,
    ResumptionRecord,
    SLAConfiguration,
    VacationPeriod,
    WorkflowTask,
)

P_CREATE, P_WITHDRAW = "elm.request.create", "elm.request.withdraw"
P_POLICY, P_ACCOUNT, P_CALENDAR = "elm.policy.manage", "elm.account.manage", "elm.calendar.manage"
P_SLA = "elm.sla.manage"
P_REVIEW = "elm.workflow.review"


def _require(actor, code):
    if actor is None or not actor.has_permission(code):
        raise PermissionDeniedError()


def _category(code):
    try:
        return LeaveCategory.objects.get(code=code, is_active=True)
    except LeaveCategory.DoesNotExist as exc:
        raise ConflictError(
            "Leave category is not configured.", code="leave_category_unconfigured"
        ) from exc


def _employee(user_id, lock=False):
    try:
        qs = EmployeeContext.objects.filter(user_id=user_id, is_active=True)
        if lock:
            qs = qs.select_for_update()
        return qs.get()
    except EmployeeContext.DoesNotExist as exc:
        raise ConflictError(
            "Active employee context is not configured.", code="employee_context_missing"
        ) from exc


def _calendar():
    return HolidayCalendar.objects.filter(is_published=True).first()


def _dates(kind):
    cal = _calendar()
    return (
        set(CalendarEntry.objects.filter(calendar=cal, kind=kind).values_list("day", flat=True))
        if cal
        else set()
    )


def _route_for(employee, category):
    if employee.is_director:
        return {
            "unit_head_user_id": employee.user_id,
            "final_authority_user_id": employee.user_id,
            "final_authority_role": "Director",
            "establishment_user_id": None,
            "establishment_required": False,
            "director_applicant": True,
        }
    options = []
    for route in ApprovalRoute.objects.filter(
        employee_kind=employee.employee_kind, category=category.code, is_active=True
    ):
        if route.organizational_unit and route.organizational_unit != employee.organizational_unit:
            continue
        if route.designation and route.designation != employee.designation:
            continue
        options.append(route)
    if not options:
        raise ConflictError(
            "No current approval route matches the employee and category.",
            code="approval_route_missing",
        )
    route = max(
        options,
        key=lambda r: (bool(r.organizational_unit), bool(r.designation), r.updated_at, r.pk),
    )
    if not employee.unit_head_user_id:
        raise ConflictError("Employee Unit Head is not configured.", code="unit_head_missing")
    return {
        "unit_head_user_id": employee.unit_head_user_id,
        "final_authority_user_id": route.final_authority_user_id,
        "final_authority_role": route.final_authority_role,
        "establishment_user_id": route.establishment_user_id,
        "establishment_required": route.establishment_required,
        "director_applicant": employee.is_director,
    }


def _split(category, start, end, half=""):
    try:
        return policy.split_days_by_year(
            category=category.code,
            start=start,
            end=end,
            half_day=half,
            counting_rule=category.counting_rule,
            closed_dates=_dates("closed"),
            restricted_dates=_dates("restricted"),
        )
    except ValueError as exc:
        raise ConflictError(str(exc), code="leave_dates_invalid") from exc


def _validate_vacation(employee, category, start, end):
    if category.code == "VL":
        if employee.employee_kind != "faculty":
            raise ConflictError(
                "Vacation Leave is for faculty only.", code="leave_category_ineligible"
            )
        if not any(
            p.starts_on <= start and p.ends_on >= end
            for p in VacationPeriod.objects.filter(is_active=True)
        ):
            raise ConflictError(
                "Vacation Leave must fit a current Academic Calendar vacation period.",
                code="academic_vacation_required",
            )


def _overlap(user_id, start, end, half, category, exclude_id=None):
    qs = LeaveRequest.objects.filter(
        employee_user_id=user_id,
        status__in=(*workflow.PENDING_STATES, workflow.APPROVED),
        request_type__in=("new", "extension", "offline"),
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return any(
        policy.overlaps(
            first_start=start,
            first_end=end,
            first_half=half,
            second_start=r.starts_on,
            second_end=r.ends_on,
            second_half=r.half_day,
            first_category=category,
            second_category=r.category.code,
        )
        for r in qs.select_related("category")
    )


def _check_substitute(uid, applicant, start, end, category):
    if uid == applicant:
        raise ConflictError(
            "The applicant cannot be their own substitute.", code="substitute_is_applicant"
        )
    _employee(uid)
    if _overlap(uid, start, end, "", category):
        raise ConflictError(
            "Substitute has overlapping pending or approved leave.", code="substitute_unavailable"
        )


def _balance(account, with_reservations=False):
    total = account.annual_entitlement + account.opening_balance
    total += LeaveTransaction.objects.filter(account=account).aggregate(v=Sum("amount"))[
        "v"
    ] or Decimal("0")
    if with_reservations:
        total -= LeaveReservation.objects.filter(account=account, is_active=True).aggregate(
            v=Sum("amount")
        )["v"] or Decimal("0")
    return total


def _reserve(request, amounts):
    found = []
    for year, amount in sorted(amounts.items()):
        account = (
            LeaveAccount.objects.select_for_update()
            .filter(user_id=request.employee_user_id, category=request.category, year=year)
            .first()
        )
        if not account:
            raise ConflictError(
                f"No {request.category.code} account for {year}.", code="leave_account_missing"
            )
        if _balance(account, True) < amount:
            raise ConflictError(
                f"Insufficient {request.category.code} balance for {year}.",
                code="leave_balance_insufficient",
            )
        found.append((account, amount))
    for account, amount in found:
        LeaveReservation.objects.create(request=request, account=account, amount=amount)


def _notify(uid, request, kind, title, body, payload=None):
    ELMNotification.objects.create(
        user_id=uid, request=request, kind=kind, title=title, body=body, payload=payload or {}
    )


def _event(request, kind, actor=None, old=None, note="", data=None):
    LeaveEvent.objects.create(
        request=request,
        from_status=old if old is not None else request.status,
        to_status=request.status,
        event_type=kind,
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=getattr(actor, "active_role", "") or "",
        note=note,
        data=data or {},
    )


def _audit_admin(actor, target_type, target_id, event_type, details):
    def safe(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {str(k): safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        return value if value is None or isinstance(value, (str, int, float, bool)) else str(value)

    AdminAuditEvent.objects.create(
        actor_user_id=actor.user_id,
        target_type=target_type,
        target_id=target_id,
        event_type=event_type,
        details=safe(details),
    )


def _task(request, kind, assignee):
    sla = SLAConfiguration.objects.filter(task_type=kind, is_active=True).first()
    row = WorkflowTask.objects.create(
        request=request,
        task_type=kind,
        assigned_to_user_id=assignee,
        reminder_after_hours=sla.reminder_after_hours if sla else None,
        escalation_after_hours=sla.escalation_after_hours if sla else None,
        escalation_user_id=sla.escalation_user_id if sla else None,
    )
    _notify(
        assignee,
        request,
        "task_assigned",
        "Leave action assigned",
        f"A {kind.replace('_', ' ')} action is waiting.",
        {"task_id": row.pk},
    )
    return row


def _close_tasks(request):
    request.tasks.filter(status="pending").update(status="cancelled", completed_at=timezone.now())


def _status(request, new, event, actor=None, note="", data=None):
    old = request.status
    request.status = new
    request.save(update_fields=["status", "updated_at"])
    _event(request, event, actor=actor, old=old, note=note, data=data)


def _release(request):
    request.reservations.filter(is_active=True).update(is_active=False)


def _charge(request, actor_id):
    for reservation in request.reservations.select_related("account").filter(is_active=True):
        LeaveTransaction.objects.create(
            account=reservation.account,
            request=request,
            kind="charge",
            amount=-reservation.amount,
            actor_user_id=actor_id,
            reference=f"leave:{request.pk}",
            note="Approved leave charge.",
        )
        reservation.is_active = False
        reservation.save(update_fields=["is_active", "updated_at"])


def _create_request(
    *,
    actor,
    category,
    start,
    end,
    reason,
    half_day="",
    station_leave=False,
    station_leave_details="",
    substitute_required=False,
    substitute_user_id=None,
    evidence_reference="",
    request_type="new",
    original=None,
    reserve=True,
):
    _require(actor, P_CREATE)
    employee = _employee(actor.user_id, lock=True)
    if category.requires_medical_evidence and not evidence_reference.strip():
        raise ConflictError(
            "This category requires medical evidence.", code="medical_evidence_required"
        )
    if category.employee_scope not in ("all", employee.employee_kind):
        raise ConflictError(
            "This category is not available to this employee.", code="leave_category_ineligible"
        )
    _validate_vacation(employee, category, start, end)
    if request_type in ("new", "extension") and _overlap(
        actor.user_id,
        start,
        end,
        half_day,
        category.code,
        exclude_id=original.pk if request_type == "extension" and original else None,
    ):
        raise ConflictError(
            "Requested dates overlap pending or approved leave.", code="leave_overlap"
        )
    if substitute_required and not substitute_user_id:
        raise ConflictError("Choose one substitute before submitting.", code="substitute_required")
    if substitute_user_id:
        _check_substitute(substitute_user_id, actor.user_id, start, end, category.code)
    amounts = _split(category, start, end, half_day)
    total = sum(amounts.values(), Decimal("0"))
    if total <= 0:
        raise ConflictError(
            "Selected dates have no chargeable leave days.", code="zero_chargeable_days"
        )
    route = _route_for(employee, category)
    state = workflow.AWAITING_SUBSTITUTE if substitute_user_id else workflow.AWAITING_UNIT_HEAD
    if route["director_applicant"] and not substitute_user_id:
        state = workflow.AWAITING_DIRECTOR
    request = LeaveRequest.objects.create(
        employee_user_id=actor.user_id,
        category=category,
        request_type=request_type,
        status=state,
        starts_on=start,
        ends_on=end,
        chargeable_days=total,
        half_day=half_day,
        reason=reason,
        station_leave=station_leave,
        station_leave_details=station_leave_details,
        substitute_required=substitute_required,
        substitute_user_id=substitute_user_id,
        substitute_response="pending" if substitute_user_id else "accepted",
        evidence_reference=evidence_reference,
        original_leave=original,
        route_snapshot=route,
    )
    if reserve:
        _reserve(request, amounts)
    _event(
        request,
        "submitted",
        actor=actor,
        old="",
        data={"chargeable_days": str(total), "request_type": request_type},
    )
    if substitute_user_id:
        _task(request, "substitute", substitute_user_id)
    elif state == workflow.AWAITING_DIRECTOR:
        _task(request, "final", actor.user_id)
    else:
        _task(request, "unit_head", route["unit_head_user_id"])
    return request


@transaction.atomic
def submit(
    *,
    actor,
    category_code,
    starts_on,
    ends_on,
    reason,
    half_day="",
    station_leave=False,
    station_leave_details="",
    substitute_required=False,
    substitute_user_id=None,
    evidence_reference="",
):
    category = _category(category_code)
    if category.code == "RH" and not _calendar():
        raise ConflictError("A published RH calendar is required.", code="holiday_calendar_missing")
    return _create_request(
        actor=actor,
        category=category,
        start=starts_on,
        end=ends_on,
        reason=reason,
        half_day=half_day,
        station_leave=station_leave,
        station_leave_details=station_leave_details,
        substitute_required=substitute_required,
        substitute_user_id=substitute_user_id,
        evidence_reference=evidence_reference,
    )


def _request(pk, lock=False):
    qs = LeaveRequest.objects.select_related("category")
    if lock:
        qs = qs.select_for_update(of=("self",))
    try:
        return qs.get(pk=pk)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.") from exc


def _owner(request, actor):
    if actor is None or actor.user_id != request.employee_user_id:
        raise PermissionDeniedError()


@transaction.atomic
def withdraw(*, request_id, actor):
    request = _request(request_id, True)
    _owner(request, actor)
    _require(actor, P_WITHDRAW)
    if request.status not in workflow.PENDING_STATES:
        raise ConflictError("Only a pending request can be withdrawn.", code="request_not_pending")
    recipients = set(request.tasks.values_list("assigned_to_user_id", flat=True))
    _release(request)
    _close_tasks(request)
    _status(request, workflow.WITHDRAWN, "withdrawn", actor)
    for uid in recipients - {actor.user_id}:
        _notify(
            uid,
            request,
            "request_withdrawn",
            "Leave request withdrawn",
            "The applicant withdrew this request.",
        )
    return request


@transaction.atomic
def substitute_response(*, request_id, actor, accept, replacement_user_id=None):
    request = _request(request_id, True)
    if request.status == workflow.APPLICANT_ACTION_REQUIRED:
        _owner(request, actor)
        if not replacement_user_id:
            raise ConflictError(
                "Choose a replacement substitute or withdraw.",
                code="replacement_substitute_required",
            )
        _check_substitute(
            replacement_user_id,
            actor.user_id,
            request.starts_on,
            request.ends_on,
            request.category.code,
        )
        request.substitute_user_id = replacement_user_id
        request.substitute_response = "pending"
        request.save(update_fields=["substitute_user_id", "substitute_response", "updated_at"])
        _status(request, workflow.AWAITING_SUBSTITUTE, "substitute_replaced", actor)
        _task(request, "substitute", replacement_user_id)
        return request
    if request.status != workflow.AWAITING_SUBSTITUTE:
        raise ConflictError(
            "This request is not waiting for substitute response.",
            code="substitute_response_not_due",
        )
    if actor.user_id != request.substitute_user_id:
        raise PermissionDeniedError()
    request.substitute_response = "accepted" if accept else "declined"
    request.save(update_fields=["substitute_response", "updated_at"])
    request.tasks.filter(task_type="substitute", status="pending").update(
        status="completed", completed_at=timezone.now()
    )
    if accept:
        _event(request, "substitute_accepted", actor)
        if request.route_snapshot.get("director_applicant"):
            _status(request, workflow.AWAITING_DIRECTOR, "routed_to_director")
            _task(request, "final", request.employee_user_id)
        else:
            _status(request, workflow.AWAITING_UNIT_HEAD, "routed_to_unit_head")
            _task(request, "unit_head", request.route_snapshot["unit_head_user_id"])
    else:
        _status(request, workflow.APPLICANT_ACTION_REQUIRED, "substitute_declined", actor)
        _notify(
            request.employee_user_id,
            request,
            "substitute_declined",
            "Replace the substitute or withdraw",
            "The proposed substitute declined.",
        )
    return request


def _consume_task(request, actor, types: Iterable[str]):
    _require(actor, P_REVIEW)
    task = request.tasks.filter(
        assigned_to_user_id=actor.user_id, status="pending", task_type__in=list(types)
    ).first()
    if task is None:
        raise PermissionDeniedError("No matching action is assigned.")
    return task


def _complete(task):
    task.status, task.completed_at = "completed", timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])


def _reject(request, actor, note):
    _release(request)
    _close_tasks(request)
    request.final_decision_by_user_id, request.decided_at = actor.user_id, timezone.now()
    _status(request, workflow.REJECTED, "rejected", actor, note)
    _notify(
        request.employee_user_id,
        request,
        "decision",
        "Leave request not approved",
        note or "The final authority did not approve this request.",
    )


def _approve(request, actor):
    if request.request_type == "cancellation":
        original = LeaveRequest.objects.select_for_update().get(pk=request.original_leave_id)
        for tx in original.transactions.select_related("account").filter(
            kind__in=("charge", "offline")
        ):
            LeaveTransaction.objects.create(
                account=tx.account,
                request=request,
                kind="reversal",
                amount=-tx.amount,
                actor_user_id=actor.user_id,
                reference=f"cancellation:{request.pk}",
                note="Approved cancellation reversal.",
            )
        original.status = workflow.CANCELLED
        original.save(update_fields=["status", "updated_at"])
        _event(
            original, "cancellation_approved", actor, data={"cancellation_request_id": request.pk}
        )
    elif request.request_type != "offline":
        _charge(request, actor.user_id)
    _close_tasks(request)
    request.final_decision_by_user_id, request.decided_at = actor.user_id, timezone.now()
    _status(request, workflow.APPROVED, "approved", actor)
    _notify(
        request.employee_user_id,
        request,
        "decision",
        "Leave request approved",
        "The final authority approved the leave request.",
    )


@transaction.atomic
def review(*, request_id, actor, action, note=""):
    request = _request(request_id, True)
    types = {
        workflow.AWAITING_UNIT_HEAD: ("unit_head",),
        workflow.AWAITING_ESTABLISHMENT: ("establishment",),
        workflow.AWAITING_FINAL: ("final",),
        workflow.AWAITING_DIRECTOR: ("final",),
    }.get(request.status)
    if not types:
        raise ConflictError("This request is not waiting for review.", code="review_not_due")
    task = _consume_task(request, actor, types)
    if task.task_type == "unit_head" and request.category.code not in {"CL", "RH"}:
        if action not in {"recommend", "not_recommended"}:
            raise ConflictError(
                "Unit Head records a recommendation, not a final decision.",
                code="recommendation_required",
            )
        _complete(task)
        route = request.route_snapshot
        if route["establishment_required"]:
            assignee, state, kind = (
                route["establishment_user_id"],
                workflow.AWAITING_ESTABLISHMENT,
                "establishment",
            )
            if not assignee:
                raise ConflictError(
                    "Establishment routing lacks an officer.", code="establishment_missing"
                )
        else:
            assignee, state, kind = (
                route["final_authority_user_id"],
                workflow.AWAITING_FINAL,
                "final",
            )
        _status(request, state, "unit_head_reviewed", actor, note, {"recommendation": action})
        _task(request, kind, assignee)
        return request
    if task.task_type == "establishment":
        if action not in {"continue", "recommend", "not_recommended"}:
            raise ConflictError(
                "Establishment must record its review and route onward.",
                code="invalid_establishment_action",
            )
        _complete(task)
        _status(
            request,
            workflow.AWAITING_FINAL,
            "establishment_reviewed",
            actor,
            note,
            {"action": action},
        )
        _task(request, "final", request.route_snapshot["final_authority_user_id"])
        return request
    if action not in {"approve", "reject"}:
        raise ConflictError(
            "Final action must be approve or reject.", code="invalid_final_decision"
        )
    _complete(task)
    _approve(request, actor) if action == "approve" else _reject(request, actor, note)
    return request


@transaction.atomic
def cancel(*, request_id, actor, reason):
    original = _request(request_id, True)
    _owner(original, actor)
    _require(actor, P_CREATE)
    if original.status != workflow.APPROVED or original.starts_on <= timezone.localdate():
        raise ConflictError(
            "Cancellation is only available before approved leave starts.",
            code="cancellation_window_closed",
        )
    if original.related_requests.filter(
        request_type="cancellation", status__in=workflow.PENDING_STATES
    ).exists():
        raise ConflictError(
            "A cancellation request is already pending.", code="cancellation_already_pending"
        )
    route = original.route_snapshot or _route_for(_employee(actor.user_id), original.category)
    state = (
        workflow.AWAITING_DIRECTOR
        if route.get("director_applicant")
        else workflow.AWAITING_UNIT_HEAD
    )
    row = LeaveRequest.objects.create(
        employee_user_id=actor.user_id,
        category=original.category,
        request_type="cancellation",
        status=state,
        starts_on=original.starts_on,
        ends_on=original.ends_on,
        chargeable_days=Decimal("0"),
        reason=reason,
        original_leave=original,
        route_snapshot=route,
        substitute_response="accepted",
    )
    _event(row, "cancellation_submitted", actor, old="")
    _task(
        row,
        "final" if state == workflow.AWAITING_DIRECTOR else "unit_head",
        actor.user_id if state == workflow.AWAITING_DIRECTOR else route["unit_head_user_id"],
    )
    return row


@transaction.atomic
def extend(
    *, request_id, actor, ends_on, reason, substitute_required=False, substitute_user_id=None
):
    original = _request(request_id, True)
    _owner(original, actor)
    if original.status != workflow.APPROVED or original.category.code not in {"EL", "COL", "VL"}:
        raise ConflictError(
            "Only approved EL, COL or VL may be extended.", code="extension_not_allowed"
        )
    if not original.starts_on <= timezone.localdate() <= original.ends_on:
        raise ConflictError(
            "Request an extension while leave is ongoing.", code="extension_window_closed"
        )
    start = original.ends_on + timedelta(days=1)
    if ends_on < start:
        raise ConflictError(
            "Extension end must follow the approved end.", code="extension_dates_invalid"
        )
    return _create_request(
        actor=actor,
        category=original.category,
        start=start,
        end=ends_on,
        reason=reason,
        substitute_required=substitute_required,
        substitute_user_id=substitute_user_id,
        request_type="extension",
        original=original,
    )


@transaction.atomic
def report_resumption(*, request_id, actor, actual_return_date, details=""):
    request = _request(request_id, True)
    _owner(request, actor)
    _require(actor, P_CREATE)
    if request.status != workflow.APPROVED or request.category.code not in {"EL", "COL", "VL"}:
        raise ConflictError(
            "Resumption is only available for approved EL, COL or VL.",
            code="resumption_not_allowed",
        )
    if actual_return_date < request.starts_on or actual_return_date > timezone.localdate():
        raise ConflictError(
            "Actual return date must be on or after leave start and not in the future.",
            code="resumption_date_invalid",
        )
    record = ResumptionRecord.objects.create(
        leave=request,
        employee_user_id=actor.user_id,
        actual_return_date=actual_return_date,
        details=details,
    )
    authority = request.route_snapshot.get("final_authority_user_id")
    if not authority:
        raise ConflictError("No final authority is configured.", code="approval_route_missing")
    _task(request, "resumption", authority)
    _event(
        request,
        "resumption_reported",
        actor,
        data={"resumption_id": record.pk, "actual_return_date": actual_return_date.isoformat()},
    )
    return record


@transaction.atomic
def review_resumption(*, resumption_id, actor, note=""):
    _require(actor, P_REVIEW)
    try:
        row = (
            ResumptionRecord.objects.select_for_update()
            .select_related("leave", "leave__category")
            .get(pk=resumption_id, status="pending")
        )
    except ResumptionRecord.DoesNotExist as exc:
        raise NotFoundError("Pending resumption record not found.") from exc
    request = _request(row.leave_id, True)
    task = request.tasks.filter(
        task_type="resumption", assigned_to_user_id=actor.user_id, status="pending"
    ).first()
    if task is None:
        raise PermissionDeniedError("No resumption review is assigned.")
    old_end = request.ends_on
    if row.actual_return_date != old_end:
        before = _split(request.category, request.starts_on, old_end)
        after = _split(request.category, request.starts_on, row.actual_return_date)
        for year in set(before) | set(after):
            account = (
                LeaveAccount.objects.select_for_update()
                .filter(user_id=request.employee_user_id, category=request.category, year=year)
                .first()
            )
            if not account:
                raise ConflictError(
                    f"No leave account is configured for {year}.", code="leave_account_missing"
                )
            delta = before.get(year, Decimal("0")) - after.get(year, Decimal("0"))
            if delta:
                LeaveTransaction.objects.create(
                    account=account,
                    request=request,
                    kind="resumption_adjustment",
                    amount=delta,
                    actor_user_id=actor.user_id,
                    reference=f"resumption:{row.pk}",
                    note=note,
                )
                row.adjustment_days += delta
        request.ends_on = row.actual_return_date
        request.chargeable_days = sum(after.values(), Decimal("0"))
        request.save(update_fields=["ends_on", "chargeable_days", "updated_at"])
    row.status, row.reviewer_user_id, row.reviewed_at = "reviewed", actor.user_id, timezone.now()
    row.save(
        update_fields=["status", "reviewer_user_id", "reviewed_at", "adjustment_days", "updated_at"]
    )
    _complete(task)
    _event(
        request,
        "resumption_reviewed",
        actor,
        note=note,
        data={"adjustment_days": str(row.adjustment_days)},
    )
    return row


@transaction.atomic
def configure_category(*, actor, values):
    _require(actor, P_POLICY)
    if values["code"] not in policy.CATEGORIES:
        raise ConflictError("Unsupported category.", code="leave_category_invalid")
    if values["code"] in policy.CONTINUOUS_CATEGORIES and values["counting_rule"] != "continuous":
        raise ConflictError(
            "EL, COL and VL must use continuous day counting.", code="continuous_counting_required"
        )
    if (
        values["code"] not in policy.CONTINUOUS_CATEGORIES
        and values["counting_rule"] == "continuous"
    ):
        raise ConflictError(
            "CL, RH and SCL cannot use continuous day counting.",
            code="noncontinuous_counting_required",
        )
    row, created = LeaveCategory.objects.update_or_create(code=values["code"], defaults=values)
    _audit_admin(actor, "leave_category", row.pk, "created" if created else "updated", values)
    return row


@transaction.atomic
def configure_employee(*, actor, values):
    _require(actor, P_POLICY)
    row, created = EmployeeContext.objects.update_or_create(
        user_id=values["user_id"], defaults=values
    )
    _audit_admin(actor, "employee_context", row.pk, "created" if created else "updated", values)
    return row


@transaction.atomic
def configure_route(*, actor, values):
    _require(actor, P_POLICY)
    keys = ("employee_kind", "organizational_unit", "designation", "category")
    row, created = ApprovalRoute.objects.update_or_create(
        **{k: values[k] for k in keys}, defaults=values
    )
    _audit_admin(actor, "approval_route", row.pk, "created" if created else "updated", values)
    return row


@transaction.atomic
def create_calendar(*, actor, name):
    _require(actor, P_CALENDAR)
    row = HolidayCalendar.objects.create(name=name, created_by_user_id=actor.user_id)
    _audit_admin(actor, "holiday_calendar", row.pk, "created", {"name": name})
    return row


@transaction.atomic
def calendar_entry(*, actor, calendar_id, day, kind, name):
    _require(actor, P_CALENDAR)
    try:
        cal = HolidayCalendar.objects.select_for_update().get(pk=calendar_id)
    except HolidayCalendar.DoesNotExist as exc:
        raise NotFoundError("Calendar not found.") from exc
    if cal.is_published:
        raise ConflictError(
            "Published calendars are immutable; create a revision.",
            code="calendar_published_immutable",
        )
    row, created = CalendarEntry.objects.update_or_create(
        calendar=cal, day=day, kind=kind, defaults={"name": name}
    )
    _audit_admin(
        actor,
        "calendar_entry",
        row.pk,
        "created" if created else "updated",
        {"calendar_id": calendar_id, "day": day, "kind": kind, "name": name},
    )
    return row


@transaction.atomic
def publish_calendar(*, actor, calendar_id):
    _require(actor, P_CALENDAR)
    try:
        cal = HolidayCalendar.objects.select_for_update().get(pk=calendar_id)
    except HolidayCalendar.DoesNotExist as exc:
        raise NotFoundError("Calendar not found.") from exc
    previous = list(HolidayCalendar.objects.filter(is_published=True).exclude(pk=cal.pk))
    for old in previous:
        old.is_published = False
        old.save(update_fields=["is_published", "updated_at"])
        _audit_admin(actor, "holiday_calendar", old.pk, "unpublished", {})
    cal.is_published, cal.published_at = True, timezone.now()
    cal.save(update_fields=["is_published", "published_at", "updated_at"])
    _audit_admin(actor, "holiday_calendar", cal.pk, "published", {"published_at": cal.published_at})
    return cal


@transaction.atomic
def configure_vacation(*, actor, name, starts_on, ends_on, source_reference=""):
    _require(actor, P_CALENDAR)
    if ends_on < starts_on:
        raise ConflictError(
            "Vacation end must not precede its start.", code="vacation_dates_invalid"
        )
    row = VacationPeriod.objects.create(
        name=name, starts_on=starts_on, ends_on=ends_on, source_reference=source_reference
    )
    _audit_admin(
        actor,
        "vacation_period",
        row.pk,
        "created",
        {
            "name": name,
            "starts_on": starts_on,
            "ends_on": ends_on,
            "source_reference": source_reference,
        },
    )
    return row


@transaction.atomic
def configure_sla(*, actor, values):
    _require(actor, P_SLA)
    if values["escalation_after_hours"] < values["reminder_after_hours"]:
        raise ConflictError("Escalation must follow the reminder.", code="sla_order_invalid")
    row, created = SLAConfiguration.objects.update_or_create(
        task_type=values["task_type"], defaults=values
    )
    _audit_admin(actor, "sla_configuration", row.pk, "created" if created else "updated", values)
    return row


@transaction.atomic
def create_account(
    *,
    actor,
    user_id,
    category_code,
    year,
    annual_entitlement,
    opening_balance=Decimal("0"),
    note="",
):
    _require(actor, P_ACCOUNT)
    category = _category(category_code)
    if not note.strip():
        raise ConflictError("Account setup requires a source note.", code="account_source_required")
    account, created = LeaveAccount.objects.get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={"annual_entitlement": annual_entitlement, "opening_balance": opening_balance},
    )
    if not created:
        account.annual_entitlement, account.opening_balance = annual_entitlement, opening_balance
        account.save(update_fields=["annual_entitlement", "opening_balance", "updated_at"])
        if note:
            LeaveTransaction.objects.create(
                account=account,
                kind="admin_adjustment",
                amount=Decimal("0"),
                actor_user_id=actor.user_id,
                reference="account-config",
                note=note,
            )
    _audit_admin(
        actor,
        "leave_account",
        account.pk,
        "created" if created else "updated",
        {
            "user_id": user_id,
            "category": category_code,
            "year": year,
            "annual_entitlement": annual_entitlement,
            "opening_balance": opening_balance,
            "note": note.strip(),
        },
    )
    return account


@transaction.atomic
def adjust_account(*, actor, user_id, category_code, year, amount, reference, note):
    _require(actor, P_ACCOUNT)
    try:
        account = LeaveAccount.objects.select_for_update().get(
            user_id=user_id, category=_category(category_code), year=year
        )
    except LeaveAccount.DoesNotExist as exc:
        raise NotFoundError("Leave account not found.") from exc
    if not reference.strip() or not note.strip():
        raise ConflictError(
            "Adjustment requires a reference and reason.", code="adjustment_evidence_required"
        )
    row = LeaveTransaction.objects.create(
        account=account,
        kind="admin_adjustment",
        amount=amount,
        actor_user_id=actor.user_id,
        reference=reference.strip(),
        note=note.strip(),
    )
    _audit_admin(
        actor,
        "leave_account",
        account.pk,
        "adjusted",
        {
            "transaction_id": row.pk,
            "amount": amount,
            "reference": reference.strip(),
            "note": note.strip(),
        },
    )
    return row


@transaction.atomic
def record_offline(
    *,
    actor,
    user_id,
    category_code,
    starts_on,
    ends_on,
    reason,
    sanction_reference,
    evidence_reference="",
):
    _require(actor, P_ACCOUNT)
    ref = sanction_reference.strip()
    if not ref:
        raise ConflictError(
            "Prior sanction reference is required.", code="offline_reference_required"
        )
    if LeaveRequest.objects.filter(request_type="offline", offline_sanction_reference=ref).exists():
        raise ConflictError(
            "This sanction was already synchronized.", code="offline_already_recorded"
        )
    employee, category = _employee(user_id, lock=True), _category(category_code)
    _validate_vacation(employee, category, starts_on, ends_on)
    if category.requires_medical_evidence and not evidence_reference.strip():
        raise ConflictError(
            "This category requires medical evidence.", code="medical_evidence_required"
        )
    amounts = _split(category, starts_on, ends_on)
    if sum(amounts.values(), Decimal("0")) <= 0:
        raise ConflictError(
            "Selected dates have no chargeable leave days.", code="zero_chargeable_days"
        )
    if _overlap(user_id, starts_on, ends_on, "", category.code):
        raise ConflictError(
            "Offline dates overlap pending or approved leave.", code="leave_overlap"
        )
    request = LeaveRequest.objects.create(
        employee_user_id=user_id,
        category=category,
        request_type="offline",
        status=workflow.APPROVED,
        starts_on=starts_on,
        ends_on=ends_on,
        chargeable_days=sum(amounts.values(), Decimal("0")),
        reason=reason,
        evidence_reference=evidence_reference,
        offline_sanction_reference=ref,
        final_decision_by_user_id=actor.user_id,
        decided_at=timezone.now(),
    )
    for year, amount in amounts.items():
        account = (
            LeaveAccount.objects.select_for_update()
            .filter(user_id=user_id, category=category, year=year)
            .first()
        )
        if not account:
            raise ConflictError(
                f"No {category.code} account for {year}.", code="leave_account_missing"
            )
        LeaveTransaction.objects.create(
            account=account,
            request=request,
            kind="offline",
            amount=-amount,
            actor_user_id=actor.user_id,
            reference=ref,
            note="Previously sanctioned leave synchronized from offline records.",
        )
    _event(request, "offline_synchronized", actor, old="", data={"reference": ref})
    _notify(
        user_id,
        request,
        "offline_synchronized",
        "Leave record synchronized",
        "A previously sanctioned leave has been synchronized to your account.",
    )
    return request
