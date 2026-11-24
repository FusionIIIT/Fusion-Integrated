# Approval hierarchy, procurement method, and SLA rules (BR-PSM-004, 008, 010, 014, 028).
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError

PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"
VALID_PRIORITIES = frozenset({PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL})

METHOD_DIRECT = "direct"
METHOD_TENDER = "tender"


@dataclass(frozen=True)
class PolicySpec:
    direct_limit: Decimal
    final_approval_threshold: Decimal
    high_priority_direct_allowed: bool
    modifiable_states: tuple[str, ...]
    withdrawable_states: tuple[str, ...]
    sla_reminder_hours: int
    sla_escalation_hours: int
    high_priority_sla_reminder_hours: int
    high_priority_sla_escalation_hours: int
    partial_payment_enabled: bool
    duplicate_window_days: int


@dataclass(frozen=True)
class SlaVerdict:
    needs_reminder: bool
    needs_escalation: bool


def select_procurement_method(estimated_cost: Decimal, policy: PolicySpec) -> str:
    """Choose direct vs. tender procurement from configured value threshold (BR-PSM-008)."""
    if estimated_cost <= Decimal("0"):
        raise ValidationRuleError("Estimated cost must be greater than zero.", code="invalid_cost")
    return METHOD_DIRECT if estimated_cost <= policy.direct_limit else METHOD_TENDER


def requires_final_approval(estimated_cost: Decimal, policy: PolicySpec) -> bool:
    """Return True when Director/Registrar final approval is required (BR-PSM-010)."""
    return estimated_cost > policy.final_approval_threshold


def allows_high_priority_direct_path(
    priority: str, estimated_cost: Decimal, policy: PolicySpec
) -> bool:
    """Return True when high/critical priority may bypass HOD review (BR-PSM-004, 014)."""
    if not policy.high_priority_direct_allowed:
        return False
    return priority in (PRIORITY_HIGH, PRIORITY_CRITICAL) and not requires_final_approval(
        estimated_cost, policy
    )


def ensure_not_self_approval(requestor_user_id: int, actor_user_id: int) -> None:
    """Prevent an approver or reviewer from approving their own indent."""
    if requestor_user_id == actor_user_id:
        raise ConflictRuleError(
            "You cannot review or approve your own indent; another authorized officer must act.",
            code="self_approval_forbidden",
        )


def ensure_rejection_reason(reason: str) -> str:
    """Require a non-empty justification when rejecting an indent (BR-PSM-005)."""
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValidationRuleError(
            "Provide a rejection justification before rejecting this indent.",
            code="rejection_reason_required",
        )
    return cleaned


def evaluate_sla(
    *,
    stage_since: datetime,
    now: datetime,
    priority: str,
    policy: PolicySpec,
    already_reminded: bool,
    already_escalated: bool,
) -> SlaVerdict:
    """Determine whether a pending approval requires SLA reminder or escalation (BR-PSM-014)."""
    is_urgent = priority in (PRIORITY_HIGH, PRIORITY_CRITICAL)
    rem_hours = policy.high_priority_sla_reminder_hours if is_urgent else policy.sla_reminder_hours
    esc_hours = (
        policy.high_priority_sla_escalation_hours if is_urgent else policy.sla_escalation_hours
    )
    elapsed = now - stage_since
    needs_escalation = not already_escalated and elapsed >= timedelta(hours=esc_hours)
    needs_reminder = (
        not already_reminded and not needs_escalation and elapsed >= timedelta(hours=rem_hours)
    )
    return SlaVerdict(needs_reminder=needs_reminder, needs_escalation=needs_escalation)
