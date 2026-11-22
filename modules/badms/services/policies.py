from datetime import UTC, datetime

from django.db import transaction

from modules.badms.models import SecurityPolicy
from modules.badms.services.audit import log_audit_event


@transaction.atomic
def save_security_policy(actor, policy_key: str, policy_value: dict) -> SecurityPolicy:
    user_id = getattr(actor, "user_id", None) or 0
    now = datetime.now(UTC)

    existing = SecurityPolicy.objects.select_for_update().filter(
        policy_key=policy_key, is_active=True
    )
    for p in existing:
        p.is_active = False
        p.effective_to = now
        p.save(update_fields=["is_active", "effective_to"])

    policy = SecurityPolicy.objects.create(
        policy_key=policy_key,
        policy_value=policy_value,
        configured_by_user_id=user_id,
        effective_from=now,
        is_active=True,
    )
    log_audit_event("security_policy_saved", actor, "SecurityPolicy", policy.id)
    return policy
