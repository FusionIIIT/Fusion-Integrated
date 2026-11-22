"""Audit-backed opening credits and balance adjustments from verified HR records."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.domain.leave import LEAVE_TYPES
from modules.hreis.models import AuditEvent, EmployeeServiceRecord, LeaveLedgerEntry
from modules.hreis.services.authz import require
from modules.hreis.services.policies import current_policy

_HR = frozenset({"hradmin"})


def _validate_credit(actor, user_id, leave_type, quantity, evidence_reference):
    if type(user_id) is not int or user_id <= 0:
        raise BadRequestError("Choose a valid employee ID.", code="invalid_employee_id")
    if user_id == actor.user_id:
        raise NotFoundError(
            "HR administrators cannot record credits for themselves. Refresh your current HR "
            "view or contact HR for help.",
            code="leave_credit_not_assigned",
        )
    if leave_type not in LEAVE_TYPES:
        raise BadRequestError("Choose a valid leave type.", code="invalid_leave_type")
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
        raise BadRequestError(
            "Credit must be a positive finite decimal. Check the submitted fields and retry.",
            code="invalid_credit",
        )
    if quantity.as_tuple().exponent < -4 or quantity >= Decimal("100000000000000"):
        raise BadRequestError(
            "Leave credit exceeds supported precision. Check the submitted fields and retry.",
            code="invalid_credit",
        )
    if (
        not isinstance(evidence_reference, str)
        or not evidence_reference.strip()
        or len(evidence_reference.strip()) > 250
    ):
        raise BadRequestError(
            "Provide a verified institutional credit evidence reference.",
            code="credit_evidence_required",
        )


def _credit_policy(user_id, leave_type):
    record = EmployeeServiceRecord.objects.select_for_update().filter(user_id=user_id).first()
    if record is None:
        raise NotFoundError(
            "Employee service record is missing. Refresh your current HR view or contact HR "
            "for help.",
            code="employee_record_missing",
        )
    from modules.directory.contracts import get_users

    user = get_users([user_id]).get(user_id)
    if user is None or user.kind not in {"faculty", "staff"}:
        raise ConflictError(
            "Employee identity could not be independently verified. Contact HR to resolve "
            "this before retrying.",
            code="employee_identity_unavailable",
        )
    policy = current_policy("leave")
    eligible = policy.parameters.get("eligibility", {}).get(user.kind, {}).get(leave_type)
    if eligible is not True:
        raise ConflictError(
            "Current policy does not permit this leave type for this employee. Contact HR to "
            "resolve this before retrying.",
            code="leave_not_eligible",
        )
    return policy


@transaction.atomic
def record_verified_credit(
    actor,
    *,
    user_id: int,
    leave_type: str,
    quantity: Decimal,
    evidence_reference: str,
    idempotency_key: str,
) -> LeaveLedgerEntry:
    """HR-CFR-007, HR-AFR-024: ledger credits require explicit provenance."""
    require(actor, "hreis.balance.manage", allowed_roles=_HR)
    _validate_credit(actor, user_id, leave_type, quantity, evidence_reference)
    if (
        not isinstance(idempotency_key, str)
        or not 1 <= len(idempotency_key) <= 100
        or not idempotency_key.strip()
    ):
        raise BadRequestError("Provide a unique operation key.", code="missing_idempotency_key")
    if LeaveLedgerEntry.objects.filter(event_key=f"leave-credit:{idempotency_key}").exists():
        raise ConflictError(
            "Leave credit already recorded. Contact HR to resolve this before retrying.",
            code="operation_replayed",
        )
    policy = _credit_policy(user_id, leave_type)
    row = LeaveLedgerEntry.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        quantity=quantity,
        policy_version=policy,
        event_key=f"leave-credit:{idempotency_key}",
        actor_user_id=actor.user_id,
    )
    AuditEvent.objects.create(
        event_key=f"leave-credit:{idempotency_key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=user_id,
        action="leave_balance_credit",
        resource_kind="leave_ledger",
        resource_id=row.pk,
        data={
            "leave_type": leave_type,
            "quantity": str(quantity),
            "evidence_reference": evidence_reference.strip(),
            "policy_version": policy.pk,
        },
    )
    return row
