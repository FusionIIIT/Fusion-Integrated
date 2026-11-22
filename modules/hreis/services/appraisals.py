"""Annual appraisal reviewer assignment and immutable in-record final archive."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory.contracts import get_users
from modules.hreis.domain import routing, workflow
from modules.hreis.models import (
    AppraisalDetail,
    AuditEvent,
    EmployeeServiceRecord,
    HRRequest,
    ServiceRecordRevision,
)
from modules.hreis.services.authz import require
from modules.hreis.services.requests import _freeze_route, _key, _route
from modules.hreis.services.transitions import _append, _route_snapshot

_ADMIN = frozenset({"hradmin"})


def _validate_reviewers(row, reviewer_user_ids):
    if (
        not isinstance(reviewer_user_ids, list)
        or not reviewer_user_ids
        or any(type(i) is not int or i <= 0 for i in reviewer_user_ids)
        or len(set(reviewer_user_ids)) != len(reviewer_user_ids)
        or row.user_id in reviewer_user_ids
    ):
        raise BadRequestError(
            "Choose distinct, verified reviewer user IDs.", code="invalid_reviewers"
        )
    users = get_users(reviewer_user_ids)
    if any(
        i not in users
        or users[i].kind not in {"faculty", "staff"}
        or not getattr(users[i], "is_active", False)
        for i in reviewer_user_ids
    ):
        raise ConflictError(
            "At least one reviewer is missing or inactive in IAM. Contact HR to resolve this "
            "before retrying.",
            code="reviewer_unknown",
        )


def _append_appraisal_archive(actor, row, detail, record):
    finalized_at = timezone.now()
    archive = {
        "kind": "appraisal",
        "request_id": row.pk,
        "period_key": detail.period_key,
        "submitted_form": detail.submitted_form,
        "reviewer_user_ids": detail.reviewer_user_ids,
        "finalized_at": finalized_at.isoformat(),
    }
    record.service_history = [*record.service_history, archive]
    record.revision += 1
    record.save(update_fields=["service_history", "revision", "updated_at"])
    ServiceRecordRevision.objects.create(
        record=record,
        revision_number=record.revision,
        snapshot={
            "appointment_details": record.appointment_details,
            "department": record.department,
            "designation_snapshot": record.designation_snapshot,
            "service_history": record.service_history,
            "retirement_status": record.retirement_status,
        },
        actor_user_id=actor.user_id,
        actor_designation=actor.active_role,
    )
    return finalized_at


@transaction.atomic
def assign_reviewers(
    actor, *, request_id: int, reviewer_user_ids: list[int], idempotency_key: str
) -> HRRequest:
    require(actor, "hreis.appraisal.assign", allowed_roles=_ADMIN)
    key = _key(idempotency_key)
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id,
            family="appraisal",
            state=workflow.SUBMITTED,
        )
        .first()
    )
    if row is None:
        raise NotFoundError(
            "Appraisal is not awaiting reviewer assignment. Refresh your current HR view or "
            "contact HR for help.",
            code="appraisal_not_submitted",
        )
    if row.user_id == actor.user_id:
        raise NotFoundError(
            "An HR administrator cannot assign reviewers to their own appraisal. Refresh your "
            "current HR view or contact HR for help.",
            code="appraisal_not_assigned",
        )
    _validate_reviewers(row, reviewer_user_ids)
    employee = EmployeeServiceRecord.objects.filter(user_id=row.user_id).first()
    source_users = get_users([row.user_id])
    if employee is None or row.user_id not in source_users:
        raise ConflictError(
            "Appraisal owner cannot be resolved. Contact HR to resolve this before retrying.",
            code="employee_missing",
        )
    route = _route(
        "appraisal", source_users[row.user_id].kind, employee.department, row.policy_version
    )
    move = workflow.resolve(
        "appraisal",
        "submitted",
        "assign_reviewers",
        workflow.HR_ADMINISTRATOR,
        guard_results={"reviewers_assigned": True},
    )
    row.appraisal.reviewer_user_ids = reviewer_user_ids
    row.appraisal.save(update_fields=["reviewer_user_ids"])
    _freeze_route(row, route)
    return _append(actor, row, move, key)


def _archive_if_finalized(actor, row, event, key):
    if event != "finalize":
        return
    record = EmployeeServiceRecord.objects.select_for_update().filter(user_id=row.user_id).first()
    if record is None:
        raise ConflictError(
            "The employee's service record is missing. Contact HR to resolve this before retrying.",
            code="employee_record_missing",
        )
    detail = AppraisalDetail.objects.select_for_update().get(request=row)
    if detail.finalized_at is not None:
        raise ConflictError(
            "This appraisal is already finalized. Contact HR to resolve this before retrying.",
            code="appraisal_finalized",
        )
    finalized_at = _append_appraisal_archive(actor, row, detail, record)
    detail.archive_reference = f"hreis:service-record:{record.pk}:revision:{record.revision}"
    detail.finalized_at = finalized_at
    detail.save(update_fields=["archive_reference", "finalized_at"])
    AuditEvent.objects.create(
        event_key=f"appraisal-archive:{key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=row.user_id,
        action="appraisal_archive",
        resource_kind="service_record",
        resource_id=record.pk,
        data={"appraisal_request_id": row.pk, "revision": record.revision},
    )


def _review_transition(actor, row, event):
    if row.user_id == actor.user_id or (
        row.route_step == 0 and actor.user_id not in row.appraisal.reviewer_user_ids
    ):
        raise NotFoundError(
            "This appraisal is not assigned to your current role. Refresh your current HR "
            "view or contact HR for help.",
            code="appraisal_not_assigned",
        )
    route = _route_snapshot(row)
    try:
        routing.require_current_authority(route, row.route_step, actor.active_role)
    except routing.RouteError as exc:
        raise NotFoundError(
            "This appraisal is not assigned to your current role. Refresh your current HR "
            "view or contact HR for help.",
            code="appraisal_not_assigned",
        ) from exc
    final = row.route_step == len(route.authorities) - 1
    if event == "forward" and final:
        raise ConflictError(
            "There is no later appraisal reviewer. Contact HR to resolve this before retrying.",
            code="appraisal_route_complete",
        )
    if event == "finalize" and not final:
        raise ConflictError(
            "The appraisal must reach its final authority. Contact HR to resolve this before "
            "retrying.",
            code="appraisal_not_final",
        )
    return workflow.resolve(
        "appraisal",
        row.state,
        event,
        workflow.AUTHORITY,
        guard_results={
            "current_authority": True,
            "not_final_authority": not final,
            "final_authority": final,
        },
    )


@transaction.atomic
def review_appraisal(actor, *, request_id: int, event: str, idempotency_key: str) -> HRRequest:
    require(actor, "hreis.appraisal.approve", allowed_roles=routing.AUTHORITY_DESIGNATIONS)
    if event not in {"forward", "finalize"}:
        raise BadRequestError("Choose forward or finalize.", code="invalid_appraisal_decision")
    key = _key(idempotency_key)
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id,
            family="appraisal",
            state__in=[workflow.PENDING_REVIEW, workflow.PENDING_NEXT_APPRAISAL_AUTHORITY],
        )
        .first()
    )
    if row is None:
        raise NotFoundError(
            "No pending appraisal review was found. Refresh your current HR view or contact "
            "HR for help.",
            code="appraisal_not_pending",
        )
    move = _review_transition(actor, row, event)
    _archive_if_finalized(actor, row, event, key)
    next_step = row.route_step + 1 if event == "forward" else None
    return _append(actor, row, move, key, step_after=next_step)
