"""IT Security policy administration service (CFR-BA-019, BA-UC-019, BA-UC-020)."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from modules.badms.domain.entities import ActorRole
from modules.badms.domain.rules import check_it_security_rbac_auth
from modules.badms.models import SecurityPolicy
from modules.badms.services.audit_service import record_audit_event


@transaction.atomic
def configure_security_policy(
    *,
    actor_id: int,
    actor_username: str,
    actor_role: str,
    key: str,
    policy_name: str,
    encryption_algorithm: str = "AES-256",
    is_enforced: bool = True,
    parameters: dict[str, Any] | None = None,
) -> SecurityPolicy:
    """BA-UC-020: Configure institution security policies."""
    role_enum = (
        ActorRole(actor_role) if actor_role in [r.value for r in ActorRole] else ActorRole.USER
    )
    check_it_security_rbac_auth(role_enum)

    policy, _created = SecurityPolicy.objects.update_or_create(
        key=key,
        defaults={
            "policy_name": policy_name,
            "encryption_algorithm": encryption_algorithm,
            "is_enforced": is_enforced,
            "parameters": parameters or {},
            "updated_by_id": actor_id,
        },
    )

    record_audit_event(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        event_source="security",
        action="security_policy_updated",
        resource_type="SecurityPolicy",
        resource_id=key,
        outcome="success",
        details={
            "key": key,
            "is_enforced": is_enforced,
            "encryption_algorithm": encryption_algorithm,
        },
    )

    return policy
