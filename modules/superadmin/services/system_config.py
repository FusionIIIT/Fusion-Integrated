"""Versioned and effective-dated system parameter configuration (BR-SA-035)."""

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.superadmin.models import SystemParameterPolicy
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def update_system_parameter(
    *,
    actor_user_id: int,
    parameter_key: str,
    parameter_value: dict,
    effective_from: datetime | None = None,
    ip_address: str | None = None,
) -> SystemParameterPolicy:
    # UC-SA-027 & BR-SA-035: Configure system parameter with versioning and effective dating.
    if not parameter_key or not parameter_key.strip():
        raise BadRequestError("Parameter key cannot be blank.", code="blank_parameter_key")

    now = timezone.now()
    eff_from = effective_from or now

    # Supersede previous active version.
    current_versions = SystemParameterPolicy.objects.filter(parameter_key=parameter_key).order_by(
        "-version"
    )
    next_version = 1
    if current_versions.exists():
        last = current_versions.first()
        next_version = last.version + 1
        SystemParameterPolicy.objects.filter(parameter_key=parameter_key, is_active=True).update(
            is_active=False,
            effective_to=eff_from,
        )

    new_param = SystemParameterPolicy.objects.create(
        parameter_key=parameter_key,
        parameter_value=parameter_value,
        version=next_version,
        effective_from=eff_from,
        is_active=True,
        updated_by_user_id=actor_user_id,
    )

    log_audit_event(
        event_type="SYSTEM_PARAMETER_UPDATED",
        actor_user_id=actor_user_id,
        target_entity="SystemParameterPolicy",
        target_id=parameter_key,
        ip_address=ip_address,
        action_details={"version": next_version, "effective_from": eff_from.isoformat()},
    )
    return new_param
