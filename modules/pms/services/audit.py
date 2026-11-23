"""PMS Audit Trail service (CFR-PMS-024).

Creates immutable records for all status changes, reviews, assignments, and critical operations.
"""

from __future__ import annotations

import logging
from typing import Any

from modules.pms.models import PatentApplication, PmsAuditTrail

log = logging.getLogger("fusion.pms.audit")


def log_audit(
    *,
    application: PatentApplication | None = None,
    actor_user_id: int | None = None,
    action_type: str,
    from_state: str = "",
    to_state: str = "",
    details: dict[str, Any] | None = None,
) -> PmsAuditTrail:
    """Create an append-only, immutable audit record."""
    record = PmsAuditTrail.objects.create(
        application=application,
        actor_user_id=actor_user_id,
        action_type=action_type,
        from_state=from_state,
        to_state=to_state,
        details=details or {},
    )
    log.info(
        "pms.audit: action=%s app=%s actor=%s from=%s to=%s",
        action_type,
        application.application_no if application else None,
        actor_user_id,
        from_state,
        to_state,
    )
    return record
