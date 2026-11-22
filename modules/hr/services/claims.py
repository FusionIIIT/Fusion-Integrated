from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from core.files import drive
from modules.hr.domain import state_machine
from modules.hr.models import (
    Claim,
    ClaimIntegrationStatus,
    EmployeeRecord,
    WorkflowRoute,
)
from modules.hr.services import authz, configuration, notifications
from modules.hr.services.common import audit

CLAIM_TYPES = {code for code, _ in WorkflowRoute.REQUEST_TYPES}
CPDA_TYPES = {"cpda_advance", "cpda_reimbursement"}


def _claim_for_update(claim_id: int) -> Claim:
    claim = Claim.objects.select_for_update().filter(pk=claim_id).first()
    if claim is None:
        raise NotFoundError("No such HR claim.")
    return claim


def _route_step(route: list, index: int) -> dict:
    if index < 0 or index >= len(route):
        raise ConflictError(
            "The configured approval route is invalid.", code="invalid_workflow_route"
        )
    step = route[index]
    if not isinstance(step, dict) or not step.get("approver_user_id"):
        raise ConflictError(
            "The configured approval route is invalid.", code="invalid_workflow_route"
        )
    return step


def _notify_employee(claim: Claim, *, action: str, subject: str, body: str) -> None:
    notifications.enqueue(
        recipient_user_id=claim.employee_user_id,
        topic=f"claim.{action}",
        dedupe_key=f"claim:{claim.pk}:{action}:{claim.updated_at.isoformat()}",
        subject=subject,
        body=body,
        payload={"claim_id": claim.pk, "status": claim.status},
    )


@transaction.atomic
def submit_claim(
    *,
    actor,
    request_type: str,
    purpose: str = "",
    amount: Decimal | None = None,
    form_data: dict | None = None,
    supporting_document_links: list[str] | None = None,
) -> Claim:
    authz.require(actor, "hr.claim.create")
    if request_type not in CLAIM_TYPES:
        raise ConflictError("Unsupported HR claim type.", code="invalid_claim_type")
    record = EmployeeRecord.objects.filter(user_id=actor.user_id).first()
    if record is None or record.employment_status != "active":
        raise ConflictError(
            "An active employee service record is required to submit a claim.",
            code="employee_record_required",
        )

    purpose = (purpose or "").strip()
    form_data = form_data or {}
    links = supporting_document_links or []
    documents = []
    for raw_link in links:
        try:
            drive_ref = drive.parse(raw_link)
        except drive.InvalidDriveLink as exc:
            raise ConflictError(exc.message, code=exc.code) from exc
        documents.append({"file_id": drive_ref.file_id, "url": drive_ref.url})

    if request_type in CPDA_TYPES:
        if not purpose or amount is None or amount <= 0 or not documents:
            raise ConflictError(
                "CPDA claims require a purpose, positive amount, and supporting document.",
                code="cpda_fields_required",
            )
    elif not form_data:
        raise ConflictError(
            "LTC claims must include the prescribed-form information.",
            code="ltc_form_required",
        )
    if amount is not None and amount <= 0:
        raise ConflictError("Claim amount must be positive.", code="invalid_claim_amount")

    claim = Claim.objects.create(
        employee_user_id=actor.user_id,
        employee_category=record.employee_category,
        request_type=request_type,
        purpose=purpose,
        amount=amount,
        form_data=form_data,
        supporting_documents=documents,
    )
    audit(
        actor=actor,
        entity_type="claim",
        entity_id=claim.pk,
        action="claim.submitted",
        details={"request_type": request_type, "status": claim.status},
    )
    _notify_employee(
        claim,
        action="submitted",
        subject="HR claim submitted",
        body="Your claim was submitted for HR verification.",
    )
    return claim


@transaction.atomic
def verify_claim(*, actor, claim_id: int, verified: bool, note: str = "") -> Claim:
    authz.require(actor, "hr.claim.verify")
    claim = _claim_for_update(claim_id)
    try:
        transition = state_machine.verify_claim(claim.status, verified=verified, has_route=True)
    except state_machine.InvalidTransition as exc:
        raise ConflictError(
            "Only claims awaiting HR verification can be verified.",
            code="invalid_transition",
        ) from exc

    before = claim.status
    route = None
    if verified:
        try:
            route = configuration.configured_route(
                employee_category=claim.employee_category,
                request_type=claim.request_type,
            )
        except NotFoundError as exc:
            raise ConflictError(
                "No approval route is configured for this claim.",
                code="workflow_not_configured",
            ) from exc
        first_step = _route_step(route.steps, 0)
        claim.route_snapshot = route.steps
        claim.current_authority_user_id = int(first_step["approver_user_id"])
        claim.authority_step = transition.authority_step
        claim.status = transition.state
        claim.verification_details = {
            "verified": True,
            "note": (note or "").strip(),
            "verified_by_user_id": actor.user_id,
            "verified_at": timezone.now().isoformat(),
        }
        claim.save(
            update_fields=[
                "route_snapshot",
                "current_authority_user_id",
                "authority_step",
                "status",
                "verification_details",
                "updated_at",
            ]
        )
    else:
        claim.verification_details = {
            "verified": False,
            "note": (note or "").strip(),
            "verified_by_user_id": actor.user_id,
            "verified_at": timezone.now().isoformat(),
        }
        claim.save(update_fields=["verification_details", "updated_at"])

    audit(
        actor=actor,
        entity_type="claim",
        entity_id=claim.pk,
        action="claim.verified" if verified else "claim.verification_failed",
        details={"from_status": before, "to_status": claim.status, "note": (note or "").strip()},
    )
    if verified:
        current_step = _route_step(route.steps, 0)
        notifications.enqueue(
            recipient_user_id=int(current_step["approver_user_id"]),
            topic="claim.awaiting_authority",
            dedupe_key=f"claim:{claim.pk}:authority:0",
            subject="HR claim awaiting your decision",
            body=f"A {claim.get_request_type_display()} claim is ready for review.",
            payload={"claim_id": claim.pk, "status": claim.status},
        )
    _notify_employee(
        claim,
        action="verified" if verified else "verification",
        subject="HR claim verification updated",
        body=(
            "Your claim was verified and routed."
            if verified
            else "Your claim could not be verified and remains with HR."
        ),
    )
    return claim


@transaction.atomic
def decide_claim(*, actor, claim_id: int, action: str, note: str = "") -> Claim:
    authz.require(actor, "hr.claim.approve")
    claim = _claim_for_update(claim_id)
    if claim.current_authority_user_id != actor.user_id or claim.employee_user_id == actor.user_id:
        raise NotFoundError("No such HR claim is assigned to you.")
    try:
        transition = state_machine.decide_claim(
            claim.status,
            action=action,
            authority_step=claim.authority_step,
            route_length=len(claim.route_snapshot),
        )
    except state_machine.InvalidTransition as exc:
        code = (
            "workflow_order"
            if exc.action in {"approval_must_follow_route", "no_next_authority"}
            else "invalid_transition"
        )
        raise ConflictError(
            "The requested decision is not valid at this workflow step.",
            code=code,
        ) from exc

    before = claim.status
    claim.status = transition.state
    claim.authority_step = transition.authority_step
    if action == "forward":
        next_step = _route_step(claim.route_snapshot, transition.authority_step)
        claim.current_authority_user_id = int(next_step["approver_user_id"])
    else:
        claim.current_authority_user_id = None
    claim.save(
        update_fields=[
            "status",
            "authority_step",
            "current_authority_user_id",
            "updated_at",
        ]
    )
    audit(
        actor=actor,
        entity_type="claim",
        entity_id=claim.pk,
        action=f"claim.{action}",
        details={"from_status": before, "to_status": claim.status, "note": (note or "").strip()},
    )

    if action == "forward":
        notifications.enqueue(
            recipient_user_id=claim.current_authority_user_id,
            topic="claim.forwarded",
            dedupe_key=f"claim:{claim.pk}:authority:{claim.authority_step}",
            subject="HR claim forwarded to you",
            body=f"A {claim.get_request_type_display()} claim is ready for review.",
            payload={"claim_id": claim.pk, "status": claim.status},
        )
    _notify_employee(
        claim,
        action=action,
        subject="HR claim decision updated",
        body=f"Your claim was {action} by its current approving authority.",
    )
    return claim


@transaction.atomic
def process_claim(*, actor, claim_id: int, financially_correct: bool, details: dict) -> Claim:
    authz.require(actor, "hr.claim.manage")
    claim = _claim_for_update(claim_id)
    if claim.status != state_machine.APPROVED:
        raise ConflictError("Only an approved claim can be processed.", code="invalid_transition")
    if not financially_correct:
        raise ConflictError(
            "Financial correctness must be confirmed before processing.",
            code="financial_verification_required",
        )
    if not isinstance(details, dict) or not details:
        raise ConflictError("Processing details are required.", code="processing_details_required")
    claim.status = state_machine.FINANCIAL_PROCESSING_RECORDED
    claim.processing_details = details
    claim.processed_by_user_id = actor.user_id
    claim.processed_at = timezone.now()
    claim.save(
        update_fields=[
            "status",
            "processing_details",
            "processed_by_user_id",
            "processed_at",
            "updated_at",
        ]
    )
    audit(
        actor=actor,
        entity_type="claim",
        entity_id=claim.pk,
        action="claim.financial_processing_recorded",
        details={"financially_correct": True, "processing_details": details},
    )
    _notify_employee(
        claim,
        action="processed",
        subject="HR claim processing updated",
        body="Financial processing details for your approved claim were recorded.",
    )
    return claim


@transaction.atomic
def record_integration_status(
    *,
    actor,
    claim_id: int,
    system: str,
    external_status: str,
    external_reference: str = "",
    details: dict | None = None,
) -> ClaimIntegrationStatus:
    authz.require(actor, "hr.claim.manage")
    claim = _claim_for_update(claim_id)
    if claim.status not in {
        state_machine.APPROVED,
        state_machine.FINANCIAL_PROCESSING_RECORDED,
    }:
        raise ConflictError(
            "External financial status can only be recorded for an approved claim.",
            code="invalid_transition",
        )
    if system not in {"payroll", "finance"} or not external_status.strip():
        raise ConflictError(
            "A supported system and status are required.", code="invalid_integration_status"
        )
    row = ClaimIntegrationStatus.objects.create(
        claim=claim,
        system=system,
        external_status=external_status.strip()[:100],
        external_reference=external_reference.strip()[:160],
        details=details or {},
        recorded_by_user_id=actor.user_id,
        received_at=timezone.now(),
    )
    audit(
        actor=actor,
        entity_type="claim",
        entity_id=claim.pk,
        action="claim.integration_status_recorded",
        details={
            "system": system,
            "external_status": row.external_status,
            "external_reference": row.external_reference,
        },
    )
    return row
