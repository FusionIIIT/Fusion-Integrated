"""Accountant attestations preserve processing before an external status exists."""

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
    FinancialStatusProjection.objects.create(
        claim=row.claim,
        event_key=f"financial-status:{key}",
        attested_by_user_id=actor.user_id,
        **details,
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


def _verified_claim(actor, request_id, states):
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id,
            family__in=("ltc", "cpda"),
            state__in=states,
        )
        .first()
    )
    if row is None or row.user_id == actor.user_id:
        raise NotFoundError(
            "Open the Accountant queue and choose an approved claim belonging to another employee.",
            code="claim_not_assigned",
        )
    if row.claim.hr_verified_by_user_id is None or row.policy_version_id is None:
        raise ConflictError(
            "Ask HR to complete documentary and policy verification before finance processing.",
            code="claim_verification_missing",
        )
    return row


def _review_reference(reference):
    if not isinstance(reference, str) or not reference.strip() or len(reference.strip()) > 250:
        raise BadRequestError(
            "Provide a financial review reference containing 1 to 250 characters.",
            code="financial_review_evidence_required",
        )
    return reference.strip()


@transaction.atomic
def verify_financial_correctness(actor, *, request_id, financial_review_reference, idempotency_key):
    require(actor, "hreis.finance.review", allowed_roles=_ACCOUNTANT)
    evidence = _review_reference(financial_review_reference)
    key = _key(idempotency_key)
    row = _verified_claim(actor, request_id, [workflow.APPROVED])
    if AuditEvent.objects.filter(event_key=f"financial-review:{key}").exists():
        raise ConflictError(
            "This review is recorded. Open the claim's audit history.", code="operation_replayed"
        )
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


def _financial_details(reference, source, external, status):
    evidence = _review_reference(reference)
    supplied = [value is not None for value in (source, external, status)]
    if any(supplied) and (
        not all(supplied)
        or source not in _SYSTEMS
        or status not in _STATUSES
        or not isinstance(external, str)
        or not external.strip()
        or len(external.strip()) > 250
    ):
        raise BadRequestError(
            "Provide all external status fields, or omit them until a status is available.",
            code="financial_evidence_required",
        )
    return {
        "financial_review_reference": evidence,
        "source_system": source,
        "external_status_reference": external.strip() if external is not None else None,
        "payment_status": status,
    }


def _require_financial_review(actor, row, details):
    if actor.has_permission("hreis.finance.review"):
        require(actor, "hreis.finance.review", allowed_roles=_ACCOUNTANT)
        return
    if not AuditEvent.objects.filter(
        action="financial_correctness_verified",
        resource_kind="hr_request",
        resource_id=row.pk,
        data__financial_review_reference=details["financial_review_reference"],
    ).exists():
        raise ConflictError(
            "Ask an Accountant reviewer to verify financial correctness before updating status.",
            code="financial_review_missing",
        )


def _notify_status(actor, row, key, status):
    Notification.objects.create(
        recipient_user_id=row.user_id,
        request=row,
        event_key=f"notification:financial-status:{key}",
        title=f"{row.family.upper()} external financial status updated",
        message=f"Your reported financial processing status is now {status}.",
    )
    OutboxEvent.objects.create(
        event_key=f"outbox:financial-status:{key}",
        event_type="hreis.notification",
        payload={"request_id": row.pk, "subject_user_id": row.user_id},
    )


def _update_processing(actor, row, key, details):
    previous = row.claim.financial_processing_details.get("payment_status")
    if row.claim.financial_verified_by_user_id is None or previous not in {*_STATUSES, None}:
        raise ConflictError(
            "Ask an Accountant to complete the initial review first.",
            code="financial_review_missing",
        )
    if previous in {"paid", "failed"}:
        raise ConflictError(
            "The reported status is final. Review its history instead. Contact HR to resolve "
            "this before retrying.",
            code="financial_status_final",
        )
    if details["payment_status"] is None:
        raise ConflictError(
            "Wait for an external status before adding a status update.",
            code="financial_status_unavailable",
        )
    if previous == "payment_pending" and details["payment_status"] == "processing":
        raise ConflictError(
            "Choose the current or a later external status.", code="financial_status_regression"
        )
    row.claim.financial_processing_details = details
    row.claim.save(update_fields=["financial_processing_details"])
    row.version += 1
    row.save(update_fields=["version", "updated_at"])
    _audit_status(actor, row, key, details)
    _notify_status(actor, row, key, details["payment_status"])
    return row


def _start_processing(actor, row, key, details):
    _require_financial_review(actor, row, details)
    if row.claim.financial_verified_by_user_id is not None:
        raise ConflictError(
            "Processing is recorded. Open the existing claim history.",
            code="financial_processing_recorded",
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
    row.claim.financial_verified_by_user_id = actor.user_id
    row.claim.financial_processing_details = details
    row.claim.save(update_fields=["financial_verified_by_user_id", "financial_processing_details"])
    result = _append(actor, row, move, key)
    _audit_status(actor, row, key, details)
    return result


@transaction.atomic
def record_financial_processing(
    actor,
    *,
    request_id: int,
    financial_review_reference: str,
    idempotency_key: str,
    source_system: str | None = None,
    external_status_reference: str | None = None,
    payment_status: str | None = None,
) -> HRRequest:
    require(actor, "hreis.finance.update", allowed_roles=_ACCOUNTANT)
    details = _financial_details(
        financial_review_reference, source_system, external_status_reference, payment_status
    )
    row = _verified_claim(
        actor, request_id, [workflow.APPROVED, workflow.FINANCIAL_PROCESSING_RECORDED]
    )
    key = _key(idempotency_key)
    if AuditEvent.objects.filter(event_key=f"financial-status:{key}").exists():
        raise ConflictError(
            "This status is already recorded. Open its history.", code="operation_replayed"
        )
    if row.state == workflow.FINANCIAL_PROCESSING_RECORDED:
        return _update_processing(actor, row, key, details)
    return _start_processing(actor, row, key, details)
