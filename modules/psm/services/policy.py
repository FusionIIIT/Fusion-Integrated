# Effective-dated PSM policy management (BR-PSM-028, Step 2.8).
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.psm.models import PsmPolicy
from modules.psm.services.common import audit_record


def _validate_policy_thresholds(
    direct_limit: Decimal,
    final_approval_threshold: Decimal,
    sla_reminder_hours: int,
    sla_escalation_hours: int,
    high_priority_sla_reminder_hours: int,
    high_priority_sla_escalation_hours: int,
) -> None:
    """Validate positive cost thresholds and SLA reminder < escalation ordering."""
    if direct_limit <= 0 or final_approval_threshold <= 0:
        raise DomainError("Cost thresholds must be greater than zero.", code="invalid_policy")
    if (
        sla_escalation_hours <= sla_reminder_hours
        or high_priority_sla_escalation_hours <= high_priority_sla_reminder_hours
    ):
        raise DomainError(
            "SLA escalation hours must exceed SLA reminder hours.", code="invalid_policy"
        )


_DEFAULT_PERMISSIBLE_STATES = ["draft", "submitted", "changes_requested", "department_reviewed"]


@transaction.atomic
def publish_policy(
    *,
    actor,
    direct_limit: Decimal,
    final_approval_threshold: Decimal,
    high_priority_direct_allowed: bool = True,
    modifiable_states: list[str] | None = None,
    withdrawable_states: list[str] | None = None,
    sla_reminder_hours: int = 24,
    sla_escalation_hours: int = 48,
    high_priority_sla_reminder_hours: int = 12,
    high_priority_sla_escalation_hours: int = 24,
    partial_payment_enabled: bool = True,
    duplicate_window_days: int = 14,
) -> PsmPolicy:
    """Create a new effective-dated policy version and supersede the prior active one."""
    _validate_policy_thresholds(
        direct_limit,
        final_approval_threshold,
        sla_reminder_hours,
        sla_escalation_hours,
        high_priority_sla_reminder_hours,
        high_priority_sla_escalation_hours,
    )
    latest = PsmPolicy.objects.select_for_update().order_by("-version").first()
    PsmPolicy.objects.filter(is_active=True).update(is_active=False)
    mod_states = (
        modifiable_states if modifiable_states is not None else list(_DEFAULT_PERMISSIBLE_STATES)
    )
    wd_states = (
        withdrawable_states
        if withdrawable_states is not None
        else list(_DEFAULT_PERMISSIBLE_STATES)
    )
    policy = PsmPolicy.objects.create(
        version=(latest.version + 1) if latest else 1,
        effective_from=timezone.now(),
        is_active=True,
        created_by_user_id=getattr(actor, "user_id", None) if actor else None,
        direct_limit=direct_limit,
        final_approval_threshold=final_approval_threshold,
        high_priority_direct_allowed=high_priority_direct_allowed,
        modifiable_states=mod_states,
        withdrawable_states=wd_states,
        sla_reminder_hours=sla_reminder_hours,
        sla_escalation_hours=sla_escalation_hours,
        high_priority_sla_reminder_hours=high_priority_sla_reminder_hours,
        high_priority_sla_escalation_hours=high_priority_sla_escalation_hours,
        partial_payment_enabled=partial_payment_enabled,
        duplicate_window_days=duplicate_window_days,
    )
    audit_record(
        actor=actor,
        action="policy.published",
        target_type="policy",
        target_id=policy.pk,
        to_state=f"v{policy.version}",
    )
    return policy


def seed_default_policy() -> tuple[PsmPolicy, bool]:
    """Idempotently seed version 1 of PsmPolicy if no active policy exists."""
    existing = PsmPolicy.objects.filter(is_active=True).first()
    if existing is not None:
        return existing, False
    policy = publish_policy(
        actor=None,
        direct_limit=Decimal("50000.00"),
        final_approval_threshold=Decimal("100000.00"),
    )
    return policy, True
