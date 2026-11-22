# Indent validation, eligibility, and duplicate checks (BR-PSM-001, 007, 015).
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError


@dataclass(frozen=True)
class IndentInput:
    item_description: str
    quantity: int
    estimated_cost: Decimal
    justification: str
    department: str


@dataclass(frozen=True)
class ExistingIndentRef:
    indent_id: int
    department: str
    item_description: str
    quantity: int
    submitted_at: datetime


def validate_indent_completeness(data: IndentInput) -> None:
    """Enforce BR-PSM-001 mandatory indent fields and positive numeric bounds."""
    missing: list[dict[str, str]] = []
    if not (data.item_description or "").strip():
        missing.append({"field": "item_description", "message": "Provide item details."})
    if not (data.justification or "").strip():
        missing.append(
            {"field": "justification", "message": "Provide a justification for this indent."}
        )
    if not (data.department or "").strip():
        missing.append({"field": "department", "message": "Specify the requesting department."})
    if data.quantity is None or data.quantity <= 0:
        missing.append({"field": "quantity", "message": "Enter a quantity greater than zero."})
    if data.estimated_cost is None or data.estimated_cost <= Decimal("0"):
        missing.append(
            {"field": "estimated_cost", "message": "Enter an estimated cost greater than zero."}
        )
    if missing:
        fields = ", ".join(m["field"] for m in missing)
        raise ValidationRuleError(
            f"Complete the required indent fields before submitting: {fields}.",
            code="indent_incomplete",
            details=missing,
        )


def ensure_state_permissible(
    status: str, permissible_states: list[str] | tuple[str, ...], action: str
) -> None:
    """Enforce BR-PSM-007 permissible-state gate for modify, withdraw, or cancel."""
    if status not in permissible_states:
        allowed = ", ".join(permissible_states) or "none"
        raise ConflictRuleError(
            f"Cannot {action} an indent in '{status}'. Allowed states: {allowed}.",
            code="indent_state_not_permissible",
        )


def find_potential_duplicate(
    *,
    department: str,
    item_description: str,
    quantity: int,
    now: datetime,
    window_days: int,
    candidates: list[ExistingIndentRef],
    exclude_indent_id: int | None = None,
) -> int | None:
    """Return a matching indent_id within the duplicate window for BR-PSM-015 flagging."""
    norm_dept = (department or "").strip().lower()
    norm_item = (item_description or "").strip().lower()
    cutoff = now - timedelta(days=window_days)
    for c in candidates:
        if exclude_indent_id is not None and c.indent_id == exclude_indent_id:
            continue
        if c.submitted_at < cutoff:
            continue
        if (
            c.department.strip().lower() == norm_dept
            and c.item_description.strip().lower() == norm_item
            and c.quantity == quantity
        ):
            return c.indent_id
    return None
