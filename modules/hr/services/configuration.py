from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.hr.domain import state_machine
from modules.hr.models import AppraisalWindow, EmployeeRecord, WorkflowRoute
from modules.hr.services import authz
from modules.hr.services.common import audit

REQUEST_TYPES = {code for code, _ in WorkflowRoute.REQUEST_TYPES}
EMPLOYEE_CATEGORIES = {code for code, _ in EmployeeRecord.CATEGORY}


def _validate_steps(steps: Sequence[dict]) -> list[dict]:
    if not steps:
        raise ConflictError(
            "At least one approval authority is required.", code="workflow_route_empty"
        )
    normalized = []
    user_ids = []
    for step in steps:
        if not isinstance(step, dict):
            raise ConflictError(
                "Each workflow step must be an object.", code="invalid_workflow_route"
            )
        try:
            user_id = int(step["approver_user_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ConflictError(
                "Each workflow step needs an approver_user_id.",
                code="invalid_workflow_route",
            ) from exc
        label = (step.get("authority_label") or "").strip()
        if user_id <= 0 or not label:
            raise ConflictError(
                "Each workflow step needs a valid approver and authority label.",
                code="invalid_workflow_route",
            )
        user_ids.append(user_id)
        normalized.append({"approver_user_id": user_id, "authority_label": label[:80]})
    if len(set(user_ids)) != len(user_ids):
        raise ConflictError(
            "An approver may appear only once in a route.", code="duplicate_workflow_approver"
        )
    people = directory.get_users(user_ids)
    active_user_ids = directory.held_employee_ids()
    if (
        len(people) != len(set(user_ids))
        or not set(user_ids).issubset(active_user_ids)
        or any(people[user_id].kind not in {"faculty", "staff"} for user_id in user_ids)
    ):
        raise ConflictError(
            "Workflow approvers must be active faculty or staff identities.",
            code="invalid_workflow_approver",
        )
    return normalized


@transaction.atomic
def save_workflow_route(
    *,
    actor,
    employee_category: str,
    request_type: str,
    steps: Sequence[dict],
    reminder_after_hours: int | None = None,
) -> WorkflowRoute:
    authz.require(actor, "hr.workflow.manage")
    if employee_category not in EMPLOYEE_CATEGORIES or request_type not in REQUEST_TYPES:
        raise ConflictError(
            "Unsupported employee category or claim type.", code="invalid_workflow_route"
        )
    if reminder_after_hours is not None and reminder_after_hours < 1:
        raise ConflictError(
            "Reminder delay must be at least one hour.", code="invalid_reminder_delay"
        )
    if request_type.startswith("leave_") and not state_machine.supports_leave_route_length(
        len(steps)
    ):
        raise ConflictError(
            "A leave route may have at most one forwarding authority.",
            code="leave_route_too_long",
        )
    normalized = _validate_steps(steps)
    route, _ = WorkflowRoute.objects.update_or_create(
        employee_category=employee_category,
        request_type=request_type,
        defaults={
            "steps": normalized,
            "reminder_after_hours": reminder_after_hours,
            "updated_by_user_id": actor.user_id,
        },
    )
    audit(
        actor=actor,
        entity_type="workflow_route",
        entity_id=route.pk,
        action="workflow.route_saved",
        details={
            "employee_category": employee_category,
            "request_type": request_type,
            "step_count": len(normalized),
            "reminder_after_hours": reminder_after_hours,
        },
    )
    return route


@transaction.atomic
def save_appraisal_window(
    *, actor, period: str, opens_at: datetime, closes_at: datetime, is_active: bool = True
) -> AppraisalWindow:
    authz.require(actor, "hr.workflow.manage")
    if not period.strip() or closes_at <= opens_at:
        raise ConflictError(
            "The appraisal period and window must be valid.", code="invalid_appraisal_window"
        )
    window, _ = AppraisalWindow.objects.update_or_create(
        period=period.strip(),
        defaults={
            "opens_at": opens_at,
            "closes_at": closes_at,
            "is_active": is_active,
            "updated_by_user_id": actor.user_id,
        },
    )
    audit(
        actor=actor,
        entity_type="appraisal_window",
        entity_id=window.pk,
        action="appraisal.window_saved",
        details={
            "period": window.period,
            "opens_at": opens_at.isoformat(),
            "closes_at": closes_at.isoformat(),
            "is_active": is_active,
        },
    )
    return window


def configured_route(*, employee_category: str, request_type: str) -> WorkflowRoute:
    route = WorkflowRoute.objects.filter(
        employee_category=employee_category, request_type=request_type
    ).first()
    if route is None or not route.steps:
        raise NotFoundError("No approval route is configured for this claim.")
    return route
