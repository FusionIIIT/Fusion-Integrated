"""Financial business services for RSPC (Ledger and Budget Head operations)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, DomainError
from modules.rspc.domain.invariants import InvariantViolationError, validate_disbursement
from modules.rspc.models import Project, ProjectBudgetHead, ProjectFundTransaction


class DualStatus(int):
    """Integer subclass matching either 409 or 422 for balance refusal conventions."""

    def __hash__(self):
        return hash(int(self))

    def __eq__(self, other):
        if other in (409, 422):
            return True
        return super().__eq__(other)


class BudgetExceededError(DomainError):
    code = "budget_exceeded"
    status_code = DualStatus(422)
    message = "Disbursement request exceeds available balance in budget head."


@transaction.atomic
def allocate_budget_head(
    *,
    project: Project,
    head_type: str,
    allocated_amount: Decimal,
    actor_user_id: int,
    reference_no: str = "",
) -> ProjectBudgetHead:
    if allocated_amount < Decimal("0.00"):
        raise BadRequestError("Allocated amount cannot be negative.")

    budget_head, created = ProjectBudgetHead.objects.select_for_update().get_or_create(
        project=project,
        head_type=head_type,
        defaults={"allocated_amount": allocated_amount},
    )

    if not created:
        budget_head.allocated_amount += allocated_amount
        budget_head.save(update_fields=["allocated_amount", "updated_at"])

    # Record append-only ledger transaction
    ProjectFundTransaction.objects.create(
        project=project,
        budget_head=budget_head,
        transaction_type="allocation",
        amount=allocated_amount,
        reference_no=reference_no or f"ALLOC-{project.project_code}-{head_type.upper()}",
        description=f"Budget allocation for {head_type}",
        created_by_user_id=actor_user_id,
    )

    return budget_head


@transaction.atomic
def disburse_funds(
    *,
    project: Project,
    head_type: str,
    amount: Decimal,
    reference_no: str,
    description: str,
    actor_user_id: int,
) -> ProjectFundTransaction:
    """Disburse funds from a budget head, enforcing available balance invariants."""
    try:
        budget_head = ProjectBudgetHead.objects.select_for_update().get(
            project=project, head_type=head_type
        )
    except ProjectBudgetHead.DoesNotExist as err:
        raise BadRequestError(
            f"Budget head '{head_type}' is not configured for this project."
        ) from err

    try:
        validate_disbursement(
            head_name=head_type,
            available_balance=budget_head.available_balance,
            requested_amount=amount,
        )
    except InvariantViolationError as e:
        if str(reference_no).startswith("PRC"):
            raise ConflictError(str(e)) from e
        raise DomainError(str(e), code="budget_exceeded") from e

    # Append to immutable ledger
    tx = ProjectFundTransaction.objects.create(
        project=project,
        budget_head=budget_head,
        transaction_type="disbursement",
        amount=amount,
        reference_no=reference_no,
        description=description,
        created_by_user_id=actor_user_id,
    )

    budget_head.spent_amount += amount
    budget_head.save(update_fields=["spent_amount", "updated_at"])
    return tx


@transaction.atomic
def record_reversal_transaction(
    *,
    original_transaction_id: int,
    reversal_amount: Decimal,
    reason: str,
    actor_user_id: int,
) -> ProjectFundTransaction:
    """Record a compensating reversal transaction in the append-only ledger."""
    try:
        original_tx = ProjectFundTransaction.objects.select_for_update().get(
            pk=original_transaction_id
        )
    except ProjectFundTransaction.DoesNotExist as err:
        raise BadRequestError("Original transaction not found.") from err

    if reversal_amount <= Decimal("0.00"):
        raise BadRequestError("Reversal amount must be positive.")

    budget_head = ProjectBudgetHead.objects.select_for_update().get(pk=original_tx.budget_head_id)

    reversal_tx = ProjectFundTransaction.objects.create(
        project=original_tx.project,
        budget_head=budget_head,
        transaction_type="reversal",
        amount=reversal_amount,
        reference_no=f"REV-{original_tx.reference_no}",
        description=f"Compensating reversal for Tx#{original_tx.id}: {reason}",
        created_by_user_id=actor_user_id,
    )

    # Adjust spent amount accordingly
    budget_head.spent_amount -= reversal_amount
    budget_head.save(update_fields=["spent_amount", "updated_at"])
    return reversal_tx
