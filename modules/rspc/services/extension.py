"""Extension and Closure services for RSPC."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.rspc.domain.invariants import InvariantViolationError, validate_extension_request
from modules.rspc.models import Project, ProjectClosureRequest, ProjectExtensionRequest


@transaction.atomic
def request_project_extension(
    *,
    project: Project,
    requested_end_date: datetime.date,
    months_requested: int,
    justification: str,
    actor_user_id: int,
) -> ProjectExtensionRequest:
    if project.user_id != actor_user_id:
        raise BadRequestError("Only the Principal Investigator may request an extension.")

    req = ProjectExtensionRequest.objects.create(
        project=project,
        requested_end_date=requested_end_date,
        months_requested=months_requested,
        justification=justification,
        status="submitted",
    )
    project.status = "extension_requested"
    project.save(update_fields=["status", "updated_at"])
    return req


@transaction.atomic
def review_project_extension(
    *,
    extension_request: ProjectExtensionRequest,
    approved: bool,
    actor_user_id: int,
    actor_role: str,
    comments: str = "",
) -> ProjectExtensionRequest:
    project = extension_request.project
    cumulative = sum(
        r.months_requested
        for r in project.extension_requests.filter(status="dean_approved").exclude(
            pk=extension_request.pk
        )
    )

    if approved:
        try:
            validate_extension_request(
                requested_months=extension_request.months_requested,
                cumulative_months=cumulative,
                approver_role=actor_role,
            )
        except InvariantViolationError as e:
            raise ConflictError(str(e)) from e

        extension_request.status = "dean_approved"
        project.end_date = extension_request.requested_end_date
        project.status = "active"
    else:
        extension_request.status = "rejected"
        project.status = "active"

    extension_request.reviewed_by_user_id = actor_user_id
    extension_request.decision_comments = comments
    extension_request.save(
        update_fields=["status", "reviewed_by_user_id", "decision_comments", "updated_at"]
    )
    project.save(update_fields=["end_date", "status", "updated_at"])
    return extension_request


@transaction.atomic
def request_project_closure(
    *, project: Project, actor_user_id: int, remarks: str = ""
) -> ProjectClosureRequest:
    if project.user_id != actor_user_id:
        raise BadRequestError("Only the Principal Investigator may request project closure.")

    closure, _ = ProjectClosureRequest.objects.get_or_create(
        project=project,
        defaults={"status": "pending", "remarks": remarks},
    )
    project.status = "closure_pending"
    project.save(update_fields=["status", "updated_at"])
    return closure


@transaction.atomic
def approve_project_closure(*, project: Project, actor_user_id: int) -> ProjectClosureRequest:
    closure = project.closure_record
    closure.status = "approved"
    closure.closed_at = timezone.now()
    closure.closed_by_user_id = actor_user_id
    closure.save(update_fields=["status", "closed_at", "closed_by_user_id", "updated_at"])

    project.status = "closed"
    project.save(update_fields=["status", "updated_at"])
    return closure
