"""Read-only selectors for IT Security policies and alerts."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import SecurityPolicy


def list_security_policies(*, is_enforced: bool | None = None) -> QuerySet[SecurityPolicy]:
    qs = SecurityPolicy.objects.all().order_by("policy_name")
    if is_enforced is not None:
        qs = qs.filter(is_enforced=is_enforced)
    return qs


def get_security_policy_by_key(key: str) -> SecurityPolicy | None:
    return SecurityPolicy.objects.filter(key=key).first()
