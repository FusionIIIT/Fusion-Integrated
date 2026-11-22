"""Financial business services for RSPC (Ledger and Budget Head operations)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.rspc.domain.invariants import InvariantViolationError, validate_disbursement
from modules.rspc.models import Project, ProjectBudgetHead, ProjectFundTransaction


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
        raise ConflictError(str(e)) from e

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
    """Create a compensating reversing transaction in the append-only ledger."""
    try:
        orig = ProjectFundTransaction.objects.get(pk=original_transaction_id)
    except ProjectFundTransaction.DoesNotExist as err:
        raise BadRequestError(f"Transaction#{original_transaction_id} not found.") from err

    budget_head = ProjectBudgetHead.objects.select_for_update().get(pk=orig.budget_head_id)

    reversal_tx = ProjectFundTransaction.objects.create(
        project=orig.project,
        budget_head=budget_head,
        transaction_type="reversal",
        amount=reversal_amount,
        reference_no=f"REV-{orig.reference_no}",
        description=f"Reversal of Tx#{orig.pk}: {reason}",
        created_by_user_id=actor_user_id,
    )

    if orig.transaction_type == "disbursement":
        budget_head.spent_amount = max(Decimal("0.00"), budget_head.spent_amount - reversal_amount)
    elif orig.transaction_type == "allocation":
        budget_head.allocated_amount = max(
            Decimal("0.00"), budget_head.allocated_amount - reversal_amount
        )

    budget_head.save(update_fields=["spent_amount", "allocated_amount", "updated_at"])
    return reversal_tx
