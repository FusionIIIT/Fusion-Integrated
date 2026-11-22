# Shared service helpers: error translation, policy lookup, audit, notifications, and lanes.
from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.psm.domain import approval_policy as ap
from modules.psm.domain import state_machine as sm
from modules.psm.domain.errors import (
    ActorNotAllowedError,
    ConflictRuleError,
    InvalidTransitionError,
    PsmRuleError,
    ValidationRuleError,
)
from modules.psm.models import PsmAuditLog, PsmNotification, PsmPolicy
from modules.psm.selectors import scoping

log = logging.getLogger("fusion.psm")


@contextmanager
def translate_errors():
    """Translate pure-Python domain errors into platform DomainError subclasses."""
    try:
        yield
    except ValidationRuleError as exc:
        raise DomainError(exc.message, code=exc.code, details=exc.details) from exc
    except (InvalidTransitionError, ConflictRuleError) as exc:
        raise ConflictError(exc.message, code=exc.code, details=exc.details) from exc
    except ActorNotAllowedError as exc:
        raise PermissionDeniedError(exc.message, code=exc.code) from exc
    except PsmRuleError as exc:
        raise DomainError(exc.message, code=exc.code, details=exc.details) from exc


def require_active_policy() -> PsmPolicy:
    """Return the active effective-dated PSM policy or refuse cleanly (BR-PSM-028)."""
    policy = PsmPolicy.objects.filter(is_active=True).order_by("-version").first()
    if policy is None:
        raise ConflictError(
            "No active PSM policy is configured; run 'manage.py seed_psm_policy'.",
            code="policy_missing",
        )
    return policy


def policy_to_spec(policy: PsmPolicy) -> ap.PolicySpec:
    """Convert a PsmPolicy row into the pure domain PolicySpec."""
    return ap.PolicySpec(
        direct_limit=Decimal(policy.direct_limit),
        final_approval_threshold=Decimal(policy.final_approval_threshold),
        high_priority_direct_allowed=policy.high_priority_direct_allowed,
        modifiable_states=tuple(policy.modifiable_states or ()),
        withdrawable_states=tuple(policy.withdrawable_states or ()),
        sla_reminder_hours=policy.sla_reminder_hours,
        sla_escalation_hours=policy.sla_escalation_hours,
        high_priority_sla_reminder_hours=policy.high_priority_sla_reminder_hours,
        high_priority_sla_escalation_hours=policy.high_priority_sla_escalation_hours,
        partial_payment_enabled=policy.partial_payment_enabled,
        duplicate_window_days=policy.duplicate_window_days,
    )


def actor_lane_for(actor) -> str:
    """Map the principal's single active_role to its state-machine actor lane."""
    role = scoping.active_role_of(actor)
    if role in ("ps_admin", "SectionHead_PS"):
        return sm.PS_ADMIN
    if role in ("Director", "Registrar"):
        return sm.FINAL_AUTHORITY
    if role == "Accounts Admin":
        return sm.ACCOUNTS
    if role in scoping.HOD_ROLES:
        return sm.DEPT_HEAD
    if role in scoping.DEPT_ADMIN_ROLES:
        return sm.DEPT_ADMIN
    return sm.EMPLOYEE


def next_number(prefix: str) -> str:
    """Generate a collision-free unique business identifier (AFR-PSM-005)."""
    stamp = timezone.now().strftime("%Y%m%d")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def audit_record(
    *,
    actor,
    action: str,
    target_type: str,
    target_id: int,
    from_state: str = "",
    to_state: str = "",
    details: dict | None = None,
) -> PsmAuditLog:
    """Append an immutable audit entry (BR-PSM-021, AFR-PSM-087)."""
    uid = getattr(actor, "user_id", None) if actor is not None else None
    role = scoping.active_role_of(actor) if actor is not None else "system"
    row = PsmAuditLog.objects.create(
        actor_user_id=uid,
        actor_role=role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        from_state=from_state,
        to_state=to_state,
        details=details or {},
    )
    log.info("psm.audit action=%s target=%s:%s actor=%s", action, target_type, target_id, uid)
    return row


def enqueue_notification(
    *,
    topic: str,
    dedupe_key: str,
    recipient_user_id: int,
    subject: str,
    body: str,
    payload: dict | None = None,
) -> PsmNotification | None:
    """Persist an idempotent lifecycle notification in communication history (BR-PSM-006)."""
    try:
        obj, _ = PsmNotification.objects.get_or_create(
            dedupe_key=dedupe_key[:160],
            defaults={
                "topic": topic,
                "recipient_user_id": recipient_user_id,
                "subject": subject[:200],
                "body": body,
                "payload": payload or {},
                "status": "pending",
            },
        )
    except IntegrityError:
        return PsmNotification.objects.filter(dedupe_key=dedupe_key[:160]).first()
    else:
        return obj


def deliver_pending_notifications(*, limit: int = 200) -> int:
    """Mark pending PSM notifications delivered in an idempotent batch (BR-PSM-006)."""
    now = timezone.now()
    ids = list(
        PsmNotification.objects.filter(status="pending")
        .order_by("created_at")
        .values_list("pk", flat=True)[:limit]
    )
    if not ids:
        return 0
    return PsmNotification.objects.filter(pk__in=ids, status="pending").update(
        status="sent", sent_at=now
    )
