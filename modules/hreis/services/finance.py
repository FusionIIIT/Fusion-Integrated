"""Accountant-side HR-EIS claim processing; no payroll or bank execution.

Financial correctness is attested by an IAM-authorized Accountant and linked to
a reference received from the external finance/payroll process. Recording an
external status does not cause a payment or certify an external integration.
"""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.domain import workflow
from modules.hreis.models import (
    AuditEvent,
    FinancialStatusProjection,
    HRRequest,
    Notification,
    OutboxEvent,
)
from modules.hreis.services.authz import require
from modules.hreis.services.requests import _key
from modules.hreis.services.transitions import _append

_ACCOUNTANT = frozenset({"Accounts Admin"})
_SYSTEMS = frozenset({"finance", "payroll"})
_STATUSES = frozenset({"processing", "payment_pending", "paid", "failed"})


def _audit_status(actor, row, key, details):
    """Preserve each externally reported status in independent immutable records."""
    FinancialStatusProjection.objects.create(
        claim=row.claim,
        event_key=f"financial-status:{key}",
        source_system=details["source_system"],
        external_status_reference=details["external_status_reference"],
        financial_review_reference=details["financial_review_reference"],
        payment_status=details["payment_status"],
        attested_by_user_id=actor.user_id,
    )
    AuditEvent.objects.create(
        event_key=f"financial-status:{key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=row.user_id,
        action="financial_status_attested",
        resource_kind="hr_request",
        resource_id=row.pk,
        data=details,
    )


@transaction.atomic
def verify_financial_correctness(
    actor, *, request_id: int,
    financial_review_reference: str, idempotency_key: str,
) -> dict:
    """Attest correctness independently of external payment-status updates.

    The review-only role can verify an approved, HR-verified claim without
    being given permission to write externally reported payment statuses.
    """
    require(actor, "hreis.finance.review", allowed_roles=_ACCOUNTANT)
    if not isinstance(financial_review_reference, str) or not financial_review_reference.strip():
        raise BadRequestError(
            "Financial review evidence is required.", code="financial_review_evidence_required"
        )
    key = _key(idempotency_key)
    row = (
        HRRequest.objects.select_for_update()
        .filter(pk=request_id, family__in=("ltc", "cpda"), state=workflow.APPROVED)
        .first()
    )
    if row is None or row.user_id == actor.user_id:
        raise NotFoundError(
            "No approved claim is assigned for finance review.", code="claim_not_assigned"
        )
    if row.claim.hr_verified_by_user_id is None or row.policy_version_id is None:
        raise ConflictError(
            "HR verification must finish before finance review.",
            code="claim_verification_missing",
        )
    if AuditEvent.objects.filter(event_key=f"financial-review:{key}").exists():
        raise ConflictError("Financial review was already recorded.", code="operation_replayed")
    evidence = financial_review_reference.strip()
    AuditEvent.objects.create(
        event_key=f"financial-review:{key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=row.user_id,
        action="financial_correctness_verified",
        resource_kind="hr_request",
        resource_id=row.pk,
        data={"financial_review_reference": evidence},
    )
    return {
        "request_id": row.pk,
        "financial_review_reference": evidence,
        "reviewed_by_user_id": actor.user_id,
    }


@transaction.atomic
def record_financial_processing(
    actor,
    *,
    request_id: int,
    financial_review_reference: str,
    source_system: str,
    external_status_reference: str,
    payment_status: str,
    idempotency_key: str,
) -> HRRequest:
    """Record one independently checked finance-side state for an approved claim.

    Never author a status without both an Accountant attestation and a linked
    external record reference. A different actor must have submitted the claim.
    """
    require(actor, "hreis.finance.update", allowed_roles=_ACCOUNTANT)
    if (
        not isinstance(financial_review_reference, str)
        or not financial_review_reference.strip()
        or not isinstance(external_status_reference, str)
        or not external_status_reference.strip()
        or source_system not in _SYSTEMS
        or payment_status not in _STATUSES
    ):
        raise BadRequestError(
            "Record the financial review, source system, external reference and status.",
            code="financial_evidence_required",
        )
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id, family__in=("ltc", "cpda"),
            state__in=(workflow.APPROVED, workflow.FINANCIAL_PROCESSING_RECORDED),
        )
        .first()
    )
    if row is None:
        raise NotFoundError(
            "No approved financial claim is available.", code="claim_not_approved"
        )
    if row.user_id == actor.user_id:
        raise NotFoundError(
            "Accountants cannot process their own HR claims.", code="claim_not_assigned"
        )
    claim = row.claim
    if claim.hr_verified_by_user_id is None or row.policy_version_id is None:
        raise ConflictError(
            "The claim has not completed verified HR and policy processing.",
            code="claim_verification_missing",
        )
    key = _key(idempotency_key)
    if AuditEvent.objects.filter(event_key=f"financial-status:{key}").exists():
        raise ConflictError(
            "The financial status already has an audit event.", code="operation_replayed"
        )
    details = {
        "financial_review_reference": financial_review_reference.strip(),
        "source_system": source_system,
        "external_status_reference": external_status_reference.strip(),
        "payment_status": payment_status,
    }
    if row.state == workflow.APPROVED:
        if actor.has_permission("hreis.finance.review"):
            require(actor, "hreis.finance.review", allowed_roles=_ACCOUNTANT)
        elif not AuditEvent.objects.filter(
            action="financial_correctness_verified",
            resource_kind="hr_request",
            resource_id=row.pk,
            data__financial_review_reference=details["financial_review_reference"],
        ).exists():
            raise ConflictError(
                "An independent financial review must precede the status update.",
                code="financial_review_missing",
            )
    if row.state == workflow.FINANCIAL_PROCESSING_RECORDED:
        previous = claim.financial_processing_details.get("payment_status")
        if claim.financial_verified_by_user_id is None or previous not in _STATUSES:
            raise ConflictError(
                "The initial Accountant review is missing.", code="financial_review_missing"
            )
        if previous in {"paid", "failed"}:
            raise ConflictError(
                "The final reported financial status cannot be changed.",
                code="financial_status_final",
            )
        if previous == "payment_pending" and payment_status == "processing":
            raise ConflictError(
                "The financial status cannot move backwards.", code="financial_status_regression"
            )
        claim.financial_processing_details = details
        claim.save(update_fields=["financial_processing_details"])
        row.version += 1
        row.save(update_fields=["version", "updated_at"])
        _audit_status(actor, row, key, details)
        Notification.objects.create(
            recipient_user_id=row.user_id,
            request=row,
            event_key=f"notification:financial-status:{key}",
            title=f"{row.family.upper()} external financial status updated",
            message=f"Your reported financial processing status is now {payment_status}.",
        )
        OutboxEvent.objects.create(
            event_key=f"outbox:financial-status:{key}",
            event_type="hreis.notification",
            payload={"request_id": row.pk, "subject_user_id": row.user_id},
        )
        return row
    if claim.financial_verified_by_user_id is not None:
        raise ConflictError(
            "Financial processing has already been recorded.", code="financial_processing_recorded"
        )
    move = workflow.resolve(
        row.family,
        row.state,
        "record_financial_processing",
        workflow.ACCOUNTANT,
        guard_results={
            "financial_correctness_verified": True,
            "processing_status_recorded": True,
            "disbursement_details_recorded": True,
        },
    )
    claim.financial_verified_by_user_id = actor.user_id
    claim.financial_processing_details = details
    claim.save(update_fields=["financial_verified_by_user_id", "financial_processing_details"])
    result = _append(actor, row, move, key)
    _audit_status(actor, row, key, details)
    return result
