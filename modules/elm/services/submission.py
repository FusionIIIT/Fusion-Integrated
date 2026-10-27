"""Transactional leave-request submission."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.elm.domain.leave_days import UnsupportedLeaveCountingRule
from modules.elm.domain.leave_requests import (
    ExistingLeaveRequest,
    LeaveRequestValidationError,
    ensure_no_overlap,
    validate_available_balance,
    validate_leave_request,
)
from modules.elm.models import (
    LeaveApprovalStep,
    LeaveRequest,
    LeaveWorkflowAction,
    SubstituteAssignment,
)
from modules.elm.services.routing import (
    ELMDependencyUnavailable,
    get_balance_provider,
    get_vacation_calendar,
    initial_request_status,
    resolve_submission_route,
)

log = logging.getLogger("fusion.elm")

_ACTIVE_STATES = (
    LeaveRequest.Status.PENDING_SUBSTITUTE,
    LeaveRequest.Status.APPLICANT_ACTION_REQUIRED,
    LeaveRequest.Status.PENDING_UNIT_HEAD,
    LeaveRequest.Status.PENDING_ESTABLISHMENT,
    LeaveRequest.Status.PENDING_FINAL_DECISION,
    LeaveRequest.Status.PENDING_DIRECTOR_SANCTION,
    LeaveRequest.Status.APPROVED,
)


def _existing_requests(user_id: int):
    return [
        ExistingLeaveRequest(
            start_date=row.start_date,
            end_date=row.end_date,
            leave_type=row.leave_type,
            status=row.status,
            half_day=row.half_day,
        )
        for row in LeaveRequest.objects.filter(user_id=user_id)
    ]


def _lock_applicant(user_id: int) -> None:
    """Serialize overlap checks on PostgreSQL; SQLite tests remain sequential."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", (0x454C4D, user_id))


def _validate_nominee(*, actor, nominee_user_id, leave_type, start_date, end_date, half_day):
    if isinstance(nominee_user_id, bool) or not isinstance(nominee_user_id, int):
        raise PermissionDeniedError(
            "substitute_user_id must be an employee ID.", code="invalid_substitute"
        )
    if nominee_user_id == actor.user_id:
        raise BadRequestError("A substitute must be another employee.", code="self_substitute")

    try:
        nominee = directory.get_users([nominee_user_id]).get(nominee_user_id)
    except Exception as exc:
        log.warning("elm.substitute_lookup_failed error_type=%s", type(exc).__name__)
        raise ELMDependencyUnavailable(
            "The employee directory could not verify the nominated substitute."
        ) from exc
    if nominee is None:
        raise ELMDependencyUnavailable(
            "The employee directory could not confirm the nominated employee."
        )
    if nominee.kind not in {"faculty", "staff"}:
        raise BadRequestError(
            "The nominated substitute is not a known Faculty or Staff employee.",
            code="invalid_substitute",
        )

    try:
        ensure_no_overlap(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            existing_requests=_existing_requests(nominee_user_id),
        )
    except LeaveRequestValidationError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc


def _available_balance(provider, *, user_id: int, leave_type: str) -> Decimal:
    try:
        balance = provider.get_available_balance(user_id=user_id, leave_type=leave_type)
    except Exception as exc:
        log.warning("elm.balance_lookup_failed error_type=%s", type(exc).__name__)
        raise ELMDependencyUnavailable(
            "The authoritative leave balance could not be checked."
        ) from exc
    try:
        validate_available_balance(balance, Decimal("0"))
    except LeaveRequestValidationError as exc:
        raise ELMDependencyUnavailable(
            "The authoritative leave balance returned an invalid quantity."
        ) from exc
    return balance


def submit_leave_request(
    *,
    actor,
    leave_type: str,
    start_date,
    end_date,
    purpose: str,
    half_day: str | None = None,
    substitute_user_id: int | None = None,
    routing_resolver=None,
    balance_provider=None,
    vacation_calendar=None,
) -> LeaveRequest:
    """Validate, resolve, and persist one request without changing balances."""
    if getattr(actor, "kind", None) not in {"faculty", "staff"}:
        raise BadRequestError(
            "Only Faculty and Staff may submit employee leave requests.",
            code="employee_required",
        )
    if leave_type == "VL" and actor.kind != "faculty":
        raise ConflictError(
            "Vacation Leave is available only to Faculty.", code="category_ineligible"
        )

    try:
        chargeable = validate_leave_request(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose,
            half_day=half_day,
        )
    except UnsupportedLeaveCountingRule as exc:
        raise ConflictError(str(exc), code="unsupported_leave_counting_rule") from exc
    except LeaveRequestValidationError as exc:
        raise BadRequestError(exc.message, code=exc.code, details=[{"field": exc.field}]) from exc

    # PostgreSQL advisory locking closes the check/insert race for one person.
    with transaction.atomic():
        _lock_applicant(actor.user_id)
        try:
            ensure_no_overlap(
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                half_day=half_day,
                existing_requests=_existing_requests(actor.user_id),
            )
        except LeaveRequestValidationError as exc:
            raise ConflictError(exc.message, code=exc.code) from exc

        route = resolve_submission_route(
            applicant=actor,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            resolver=routing_resolver,
        )

        if route.requires_substitute and substitute_user_id is None:
            raise BadRequestError(
                "This route requires a nominated substitute.",
                code="substitute_required",
                details=[{"field": "substitute_user_id"}],
            )
        if not route.requires_substitute and substitute_user_id is not None:
            raise BadRequestError(
                "The resolved route does not require a substitute nomination.",
                code="substitute_not_required",
            )
        if substitute_user_id is not None:
            _validate_nominee(
                actor=actor,
                nominee_user_id=substitute_user_id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                half_day=half_day,
            )

        if leave_type == "VL":
            calendar = get_vacation_calendar(vacation_calendar)
            try:
                applicable = calendar.is_vacation_period(
                    user_id=actor.user_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as exc:
                log.warning("elm.vacation_calendar_failed error_type=%s", type(exc).__name__)
                raise ELMDependencyUnavailable(
                    "The Academic Calendar could not validate the VL period."
                ) from exc
            if applicable is not True:
                raise ConflictError(
                    "VL must fall within an applicable published vacation period.",
                    code="vacation_period_required",
                )

        provider = get_balance_provider(balance_provider)
        available = _available_balance(provider, user_id=actor.user_id, leave_type=leave_type)
        try:
            validate_available_balance(available, chargeable)
        except LeaveRequestValidationError as exc:
            raise ConflictError(exc.message, code=exc.code) from exc

        status = initial_request_status(route)
        request = LeaveRequest.objects.create(
            user_id=actor.user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose.strip(),
            half_day=half_day,
            chargeable_days=chargeable,
            status=status,
            submitted_at=timezone.now(),
        )
        LeaveApprovalStep.objects.bulk_create(
            [
                LeaveApprovalStep(
                    request=request,
                    sequence=index,
                    role_code=step.role_code,
                    assigned_user_id=step.assigned_user_id,
                )
                for index, step in enumerate(route.steps, start=1)
            ]
        )
        LeaveWorkflowAction.objects.create(
            request=request,
            from_status="",
            to_status=status,
            action=LeaveWorkflowAction.Action.SUBMITTED,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
        )
        if substitute_user_id is not None:
            SubstituteAssignment.objects.create(
                request=request,
                sequence=1,
                nominee_user_id=substitute_user_id,
            )
            LeaveWorkflowAction.objects.create(
                request=request,
                from_status=status,
                to_status=status,
                action=LeaveWorkflowAction.Action.SUBSTITUTE_NOMINATED,
                actor_user_id=actor.user_id,
                actor_role=actor.active_role or "",
            )
        return request
