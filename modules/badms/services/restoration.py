from datetime import UTC, datetime

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.badms.domain.state_machine import (
    InvalidStateTransitionError,
    UnauthorizedTransitionActorError,
    transition_restoration,
)
from modules.badms.models import ArchivalRequest, RestorationRequest
from modules.badms.services.audit import log_audit_event


@transaction.atomic
def request_data_restoration(
    actor, archival_request_id: int, target_destination: str
) -> RestorationRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = getattr(actor, "department", "") or ""

    archive = ArchivalRequest.objects.filter(id=archival_request_id).first()
    if not archive:
        raise NotFoundError("Archived dataset not found.")

    classification = archive.authoritative_classification or archive.initial_classification
    event = "request_sensitive" if classification == "Sensitive" else "request_non_sensitive"
    target_state = transition_restoration("none", event, "user")

    req = RestorationRequest.objects.create(
        requester_user_id=user_id,
        department=dept,
        archival_request_id=archival_request_id,
        classification=classification,
        target_destination=target_destination,
        status=target_state,
    )
    log_audit_event("restoration_requested", actor, "RestorationRequest", req.id, dept)
    return req


@transaction.atomic
def approve_sensitive_restoration(actor, restoration_id: int, decision: str) -> RestorationRequest:
    user_id = getattr(actor, "user_id", None) or 0
    req = RestorationRequest.objects.select_for_update().filter(id=restoration_id).first()
    if not req:
        raise NotFoundError("Restoration request not found.")

    event = "approve" if decision.lower() == "approve" else "reject"
    try:
        next_state = transition_restoration(req.status, event, "sysadmin")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    req.status = next_state
    req.approved_by_user_id = user_id
    req.approved_at = datetime.now(UTC)
    req.save()

    log_audit_event(
        f"restoration_{next_state}", actor, "RestorationRequest", req.id, req.department
    )
    return req


@transaction.atomic
def execute_data_restoration(actor, restoration_id: int) -> RestorationRequest:
    user_id = getattr(actor, "user_id", None) or 0
    req = RestorationRequest.objects.select_for_update().filter(id=restoration_id).first()
    if not req:
        raise NotFoundError("Restoration request not found.")

    try:
        next_state = transition_restoration(req.status, "execute", "sysadmin")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    req.status = next_state
    req.executed_by_user_id = user_id
    req.restored_at = datetime.now(UTC)
    req.save()

    log_audit_event("restoration_executed", actor, "RestorationRequest", req.id, req.department)
    return req
