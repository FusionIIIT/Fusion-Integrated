"""
Indent Write Services (PSM Module).
Enforces pure Python domain rules before persisting and guarantees transaction atomicity.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from core.api.exceptions import BadRequestError as ValidationError, NotFoundError

from modules.psm.domain.indent_state import (
    IndentState,
    can_transition,
    is_modifiable,
)
from modules.psm.domain.rules import (
    validate_indent_completeness,
    is_possible_duplicate,
    validate_rejection_justification,
)
from modules.psm.models import Indent, IndentVersion
from modules.psm.selectors.scoping import _get_principal_user_id
from modules.psm.selectors.indents import get_indent_by_id


@transaction.atomic
def create_indent(
    *,
    principal: Any,
    item_details: str,
    quantity: int,
    estimated_cost: Any,
    justification: str,
    priority: str = "NORMAL",
    status: str = "SUBMITTED",
) -> Indent:
    """Create a new Purchase Indent.

    Validates completeness and duplicate criteria, persists the Indent and creates
    the initial IndentVersion record.
    """
    requestor_id = _get_principal_user_id(principal)
    if not requestor_id:
        raise ValidationError("Valid authenticated requestor ID is required to create an indent.")

    indent_data = {
        "item_details": item_details,
        "quantity": quantity,
        "estimated_cost": estimated_cost,
        "justification": justification,
    }

    try:
        validate_indent_completeness(indent_data)
    except ValueError as e:
        raise ValidationError(str(e))

    # Check for potential duplicates against active submitted indents
    active_indents = list(
        Indent.objects.filter(
            status__in=[
                "SUBMITTED",
                "STOCK_CHECKED",
                "DEPT_REVIEWED",
                "HEAD_RECOMMENDED",
                "AWAITING_FINAL_APPROVAL",
            ]
        ).values("id", "indent_id", "item_details", "estimated_cost", "status")
    )
    duplicate_flag = is_possible_duplicate(indent_data, active_indents)

    # Generate a unique business indent_id
    year = datetime.now().year
    unique_suffix = uuid.uuid4().hex[:6].upper()
    business_id = f"IND-{year}-{unique_suffix}"

    norm_priority = str(priority).upper()
    if norm_priority not in ["NORMAL", "HIGH", "CRITICAL"]:
        norm_priority = "NORMAL"

    norm_status = str(status).upper()
    if norm_status not in [IndentState.DRAFT.value, IndentState.SUBMITTED.value]:
        norm_status = IndentState.SUBMITTED.value

    indent = Indent.objects.create(
        indent_id=business_id,
        requestor_id=requestor_id,
        item_details=item_details.strip(),
        quantity=int(quantity),
        estimated_cost=Decimal(str(estimated_cost)),
        justification=justification.strip(),
        status=norm_status,
        priority=norm_priority,
        is_duplicate=duplicate_flag,
        current_version=1,
    )

    # Create initial version history
    IndentVersion.objects.create(
        indent=indent,
        version_number=1,
        item_details=indent.item_details,
        quantity=indent.quantity,
        estimated_cost=indent.estimated_cost,
        justification=indent.justification,
    )

    return indent


@transaction.atomic
def modify_indent(
    *,
    principal: Any,
    indent_id: Any,
    **updated_fields: Any,
) -> Indent:
    """Modify an existing indent (BR-PSM-007).

    Modifiable only in DRAFT and SUBMITTED states.
    Archives current state to IndentVersion, updates Indent, and increments version.
    """
    indent = get_indent_by_id(principal, indent_id)
    if indent is None:
        raise NotFoundError("Indent not found or access denied.")

    if not is_modifiable(indent.status):
        raise ValidationError(
            f"Indent in status '{indent.status}' cannot be modified. Modification is permitted only in DRAFT or SUBMITTED status."
        )

    # Snapshot current version before mutation
    IndentVersion.objects.create(
        indent=indent,
        version_number=indent.current_version,
        item_details=indent.item_details,
        quantity=indent.quantity,
        estimated_cost=indent.estimated_cost,
        justification=indent.justification,
    )

    # Apply updates
    if "item_details" in updated_fields:
        indent.item_details = str(updated_fields["item_details"]).strip()
    if "quantity" in updated_fields:
        indent.quantity = int(updated_fields["quantity"])
    if "estimated_cost" in updated_fields:
        indent.estimated_cost = Decimal(str(updated_fields["estimated_cost"]))
    if "justification" in updated_fields:
        indent.justification = str(updated_fields["justification"]).strip()
    if "priority" in updated_fields:
        p = str(updated_fields["priority"]).upper()
        if p in ["NORMAL", "HIGH", "CRITICAL"]:
            indent.priority = p

    # Re-validate completeness
    try:
        validate_indent_completeness({
            "item_details": indent.item_details,
            "quantity": indent.quantity,
            "estimated_cost": indent.estimated_cost,
            "justification": indent.justification,
        })
    except ValueError as e:
        raise ValidationError(str(e))

    indent.current_version += 1
    indent.save()
    return indent


@transaction.atomic
def transition_indent(
    *,
    principal: Any,
    indent_id: Any,
    target_state: str,
    justification: str = "",
) -> Indent:
    """Transition an indent to a new workflow status.

    Validates transition rules and rejection justification requirements.
    """
    indent = get_indent_by_id(principal, indent_id)
    if indent is None:
        raise NotFoundError("Indent not found or access denied.")

    target_norm = str(target_state).strip().upper()

    if not can_transition(indent.status, target_norm):
        raise ValidationError(
            f"Invalid state transition from '{indent.status}' to '{target_norm}'."
        )

    try:
        validate_rejection_justification(target_norm, justification)
    except ValueError as e:
        raise ValidationError(str(e))

    indent.status = target_norm
    if target_norm in ["REJECT", "REJECTED"]:
        indent.rejection_justification = str(justification).strip()

    indent.save()
    return indent


@transaction.atomic
def withdraw_indent(
    *,
    principal: Any,
    indent_id: Any,
) -> Indent:
    """Withdraw a pending indent."""
    return transition_indent(
        principal=principal,
        indent_id=indent_id,
        target_state=IndentState.WITHDRAWN.value,
        justification="Withdrawn by requestor.",
    )
