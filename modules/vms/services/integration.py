"""Integration boundary settings (VMS-UC-002, CFR-003).

Configuration only: this module never calls an outside system. Secrets are
write-only; reads return ``***`` (or empty when unset).
"""
from __future__ import annotations

from core.api.exceptions import BadRequestError, NotFoundError
from modules.vms.models import IntegrationSetting
from modules.vms.services.common import audit, authz

PERM = "vms.integration.manage"
MASK = "***"

_STR, _BOOL, _INT, _SECRET = "str", "bool", "int", "secret"

_SERVICE = {"enabled": _BOOL, "base_url": _STR, "api_key": _SECRET}
#: key -> {field: type}. Unknown fields are rejected so a typo cannot
#: silently store nothing.
SCHEMAS: dict[str, dict[str, str]] = {
    "campus_directory": dict(_SERVICE),
    "sms_gateway": {"enabled": _BOOL, "provider": _STR, "endpoint": _STR,
                    "sender_id": _STR, "api_key": _SECRET},
    "access_control_readers": dict(_SERVICE),
    "event_management": dict(_SERVICE),
    "hostel_management": dict(_SERVICE),
    "notification_channels": {"inapp": _BOOL, "email": _BOOL, "sms": _BOOL,
                              "push": _BOOL},
    #: D-15: upper bound for a zone elevation time-box.
    "max_elevation_minutes": {"minutes": _INT},
}
KEYS = tuple(SCHEMAS)
DEFAULT_MAX_ELEVATION_MINUTES = 120


def _schema(key: str) -> dict[str, str]:
    if key not in SCHEMAS:
        raise NotFoundError("Unknown integration setting.")
    return SCHEMAS[key]


def _secret_fields(key):
    return [f for f, t in _schema(key).items() if t == _SECRET]


def _validate(key: str, value) -> dict:
    schema = _schema(key)
    if not isinstance(value, dict):
        raise BadRequestError("The value must be an object.", code="validation_error")
    unknown = sorted(set(value) - set(schema))
    if unknown:
        raise BadRequestError(f"Unknown field(s): {', '.join(unknown)}.",
                              code="validation_error")
    out = {}
    for field, kind in schema.items():
        if field not in value:
            continue
        v = value[field]
        ok = ((kind == _BOOL and isinstance(v, bool))
              or (kind in (_STR, _SECRET) and isinstance(v, str))
              or (kind == _INT and isinstance(v, int) and not isinstance(v, bool)))
        if not ok:
            raise BadRequestError(f"{field} has the wrong type.", code="validation_error")
        out[field] = v
    if key == "max_elevation_minutes":
        minutes = out.get("minutes")
        if minutes is None or not 1 <= minutes <= 1440:
            raise BadRequestError("minutes must be between 1 and 1440.",
                                  code="validation_error")
    if out.get("enabled") and "base_url" in schema:
        url = out.get("base_url", "")
        if not url.startswith(("http://", "https://")):
            raise BadRequestError("An enabled integration needs an http(s) base_url.",
                                  code="validation_error")
    return out


def _masked(key: str, value: dict) -> dict:
    out = dict(value or {})
    for f in _secret_fields(key):
        if out.get(f):
            out[f] = MASK
    return out


def get(*, actor, key: str) -> dict:
    """Stored value with secrets masked."""
    authz.require(actor, PERM)
    _schema(key)
    row = IntegrationSetting.objects.filter(key=key).first()
    return {"key": key, "value": _masked(key, row.value if row else {}),
            "updated_by_user_id": row.updated_by_user_id if row else None}


def list_all(*, actor) -> list[dict]:
    authz.require(actor, PERM)
    return [get(actor=actor, key=k) for k in KEYS]


def set_value(*, actor, key: str, value: dict) -> dict:
    """Replace the setting. A secret sent as ``***`` or omitted keeps its old value."""
    authz.require(actor, PERM)
    new = _validate(key, value)
    from django.db import transaction
    with transaction.atomic():
        row, _ = IntegrationSetting.objects.select_for_update().get_or_create(key=key)
        old = row.value or {}
        for f in _secret_fields(key):
            if new.get(f) == MASK or f not in new:
                if f in old:
                    new[f] = old[f]
                else:
                    new.pop(f, None)
        changed = sorted(f for f in set(old) | set(new) if old.get(f) != new.get(f))
        row.value = new
        row.updated_by_user_id = actor.user_id
        row.save(update_fields=["value", "updated_by_user_id"])
        # Field names only; a secret's value must never reach the audit trail.
        audit.record(actor=actor, action="vms.integration.updated", entity=row,
                     detail={"key": key, "changed_fields": changed})
    return get(actor=actor, key=key)


def max_elevation_minutes() -> int:
    """D-15 lookup for the elevation flow (lane B); default 120."""
    row = IntegrationSetting.objects.filter(key="max_elevation_minutes").first()
    minutes = (row.value or {}).get("minutes") if row else None
    return minutes if isinstance(minutes, int) and minutes > 0 \
        else DEFAULT_MAX_ELEVATION_MINUTES
