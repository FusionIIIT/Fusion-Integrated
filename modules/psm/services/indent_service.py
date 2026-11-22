from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.psm.domain.state_machines import transition_indent
from modules.psm.domain.threshold_policy import requires_director_approval
from modules.psm.domain.validators import (
    ValidationError,
    validate_indent_completeness,
    validate_rejection_reason,
)
from modules.psm.models.indent import Indent, IndentItem, IndentStatus
from modules.psm.models.item import ItemMaster


def generate_indent_number() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"IND-{timestamp}"


@transaction.atomic
def create_indent(
    user_id: int,
    department_code: str,
    title: str,
    purpose: str,
    priority: str,
    items_data: Sequence[dict[str, Any]],
) -> Indent:
    """Creates a new Indent in DRAFT status."""
    validate_indent_completeness(title, purpose, items_data)

    indent = Indent.objects.create(
        indent_number=generate_indent_number(),
        user_id=user_id,
        department_code=department_code,
        title=title,
        purpose=purpose,
        priority=priority,
        status=IndentStatus.DRAFT,
        estimated_total=Decimal("0.00"),
    )

    total_cost = Decimal("0.00")
    for item_data in items_data:
        item_master_id = item_data["item_master_id"]
        qty = int(item_data["quantity_requested"])
        unit_cost = Decimal(str(item_data.get("estimated_unit_cost", "0.00")))

        item_master = ItemMaster.objects.get(pk=item_master_id)
        indent_item = IndentItem.objects.create(
            indent=indent,
            item_master=item_master,
            quantity_requested=qty,
            estimated_unit_cost=unit_cost,
            specifications=item_data.get("specifications", ""),
        )
        total_cost += indent_item.total_cost

    indent.estimated_total = total_cost
    indent.save(update_fields=["estimated_total"])
    return indent


@transaction.atomic
def submit_indent(indent_id: int, user_id: int) -> Indent:
    """Submits a DRAFT indent for departmental approval."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)
    if indent.user_id != user_id:
        raise ValidationError("Only the indent creator may submit this indent.")

    next_state = transition_indent(indent.status, "SUBMIT", "requestor")
    indent.status = next_state
    indent.current_approver_role = "dept_admin"
    indent.save(update_fields=["status", "current_approver_role", "updated_at"])
    return indent


@transaction.atomic
def review_dept_indent(indent_id: int, user_id: int, action: str, remarks: str = "") -> Indent:
    """Department admin / HOD review."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)

    if action == "APPROVE":
        next_state = transition_indent(indent.status, "HOD_APPROVE_LOW", "hod")
        indent.status = next_state
        indent.current_approver_role = "ps_admin"
    elif action == "REJECT":
        validate_rejection_reason(remarks)
        next_state = transition_indent(indent.status, "HOD_REJECT", "hod")
        indent.status = next_state
        indent.rejection_reason = remarks
        indent.current_approver_role = ""
    else:
        raise ValidationError(f"Invalid department review action '{action}'.")

    indent.save(update_fields=["status", "current_approver_role", "rejection_reason", "updated_at"])
    return indent


@transaction.atomic
def review_ps_indent(indent_id: int, user_id: int, action: str, remarks: str = "") -> Indent:
    """Procurement & Stores admin evaluation."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)

    if action == "APPROVE":
        if requires_director_approval(indent.estimated_total):
            next_state = transition_indent(indent.status, "PS_ESCALATE_HIGH_VALUE", "ps_admin")
            indent.status = next_state
            indent.current_approver_role = "director"
        else:
            next_state = transition_indent(indent.status, "PS_APPROVE_STANDARD", "ps_admin")
            indent.status = next_state
            indent.current_approver_role = ""
    elif action == "REJECT":
        validate_rejection_reason(remarks)
        next_state = transition_indent(indent.status, "PS_REJECT", "ps_admin")
        indent.status = next_state
        indent.rejection_reason = remarks
        indent.current_approver_role = ""
    else:
        raise ValidationError(f"Invalid PS review action '{action}'.")

    indent.save(update_fields=["status", "current_approver_role", "rejection_reason", "updated_at"])
    return indent


@transaction.atomic
def review_director_indent(indent_id: int, user_id: int, action: str, remarks: str = "") -> Indent:
    """Director / Registrar final approval for high-value indents."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)

    if action == "APPROVE":
        next_state = transition_indent(indent.status, "DIRECTOR_APPROVE", "director")
        indent.status = next_state
        indent.current_approver_role = ""
    elif action == "REJECT":
        validate_rejection_reason(remarks)
        next_state = transition_indent(indent.status, "DIRECTOR_REJECT", "director")
        indent.status = next_state
        indent.rejection_reason = remarks
        indent.current_approver_role = ""
    else:
        raise ValidationError(f"Invalid Director review action '{action}'.")

    indent.save(update_fields=["status", "current_approver_role", "rejection_reason", "updated_at"])
    return indent


@transaction.atomic
def cancel_indent(indent_id: int, user_id: int) -> Indent:
    """Cancels a pending indent if allowed by BR-PSM-007."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)
    if indent.user_id != user_id:
        raise ValidationError("Only the indent creator may cancel this indent.")

    next_state = transition_indent(indent.status, "CANCEL", "requestor")
    indent.status = next_state
    indent.current_approver_role = ""
    indent.save(update_fields=["status", "current_approver_role", "updated_at"])
    return indent
