from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError
from fusion_auth.principal import Principal
from modules.superadmin.domain.constants import (
    AUDIT_ACTION_POLICY_SUPERSEDED,
    PERMITTED_CONFIG_KEYS,
)
from modules.superadmin.domain.exceptions import DomainError as PureDomainError
from modules.superadmin.domain.validators import validate_configuration_key
from modules.superadmin.models.config import SystemPolicyParameter
from modules.superadmin.services.audit import record_audit_event


@transaction.atomic
def supersede_policy_param(
    principal: Principal,
    *,
    key: str,
    value: str,
    value_type: str = "string",
    description: str = "",
) -> SystemPolicyParameter:
    # Effective-dated append-only pattern: expires previous active record and appends new version
    try:
        validate_configuration_key(key, PERMITTED_CONFIG_KEYS)
    except PureDomainError as exc:
        raise DomainError(exc.message, code=exc.code) from exc

    now = timezone.now()
    previous = (
        SystemPolicyParameter.objects.select_for_update()
        .filter(key=key, effective_to__isnull=True)
        .order_by("-version")
        .first()
    )

    next_version = 1
    if previous is not None:
        previous.effective_to = now
        previous.save(update_fields=["effective_to", "updated_at"])
        next_version = previous.version + 1

    new_param = SystemPolicyParameter.objects.create(
        key=key,
        value=value,
        value_type=value_type,
        version=next_version,
        effective_from=now,
        effective_to=None,
        description=description,
        updated_by=principal.user_id,
    )

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_POLICY_SUPERSEDED,
        target_id=key,
        target_type="policy_parameter",
        reason=f"Superseded to version {next_version}",
        context_metadata={"key": key, "new_value": value, "version": next_version},
    )
    return new_param
