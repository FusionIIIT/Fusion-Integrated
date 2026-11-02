"""Read side of the access policy (VMS-BR-125..129). Writes belong to lane C
(`services/policy_admin.py`); `publish` below is the port of the legacy publish
endpoint and is superseded by it.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from modules.vms.models import AccessPolicy, Zone
from modules.vms.services.common import audit


@dataclass(frozen=True)
class EffectivePolicy:
    """Frozen view of one published policy version (BR-127)."""
    version: int
    policy_id: int | None
    published_at: datetime.datetime | None
    visiting_hours_start: datetime.time
    visiting_hours_end: datetime.time
    max_visit_hours: int
    walk_in_pass_hours: int
    approval_timeout_hours: int
    reminder_after_hours: int
    advance_registration_hours: int
    allow_same_day_urgent: bool
    contingency_sla_minutes: int
    walkin_rate_limit_per_hour: int
    #: Zones needing explicit permission: the policy's restricted zones plus
    #: every Zone flagged is_restricted.
    restricted_zone_ids: frozenset[int]


#: Used only when nothing has ever been published (version 0). seed_vms
#: publishes v1 with the same SRS defaults.
def _defaults() -> EffectivePolicy:
    return EffectivePolicy(
        version=0, policy_id=None, published_at=None,
        visiting_hours_start=datetime.time(8, 0), visiting_hours_end=datetime.time(20, 0),
        max_visit_hours=8, walk_in_pass_hours=4, approval_timeout_hours=24,
        reminder_after_hours=12, advance_registration_hours=2,
        allow_same_day_urgent=True, contingency_sla_minutes=15,
        walkin_rate_limit_per_hour=30,
        restricted_zone_ids=frozenset(
            Zone.objects.filter(is_restricted=True).values_list("pk", flat=True)))


def _freeze(p: AccessPolicy) -> EffectivePolicy:
    restricted = set(p.restricted_zones.values_list("pk", flat=True))
    restricted.update(Zone.objects.filter(is_restricted=True).values_list("pk", flat=True))
    return EffectivePolicy(
        version=p.version, policy_id=p.pk, published_at=p.published_at,
        visiting_hours_start=p.visiting_hours_start, visiting_hours_end=p.visiting_hours_end,
        max_visit_hours=p.max_visit_hours, walk_in_pass_hours=p.walk_in_pass_hours,
        approval_timeout_hours=p.approval_timeout_hours,
        reminder_after_hours=p.reminder_after_hours,
        advance_registration_hours=p.advance_registration_hours,
        allow_same_day_urgent=p.allow_same_day_urgent,
        contingency_sla_minutes=p.contingency_sla_minutes,
        walkin_rate_limit_per_hour=p.walkin_rate_limit_per_hour,
        restricted_zone_ids=frozenset(restricted))


def _published():
    return AccessPolicy.objects.filter(status=AccessPolicy.Status.PUBLISHED)


def effective(at=None) -> EffectivePolicy:
    """Latest PUBLISHED policy (as of `at` when given). BR-127."""
    qs = _published()
    if at is not None:
        qs = qs.filter(published_at__lte=at)
    p = qs.order_by("-version").first()
    return _freeze(p) if p else _defaults()


def snapshot_for(request) -> EffectivePolicy:
    """The policy that applied when `request` was made; later publications do
    not change it (BR-129). A request older than every publication falls back
    to the oldest published version."""
    p = (_published().filter(published_at__lte=request.created_at)
         .order_by("-version").first()
         or _published().order_by("version").first())
    return _freeze(p) if p else _defaults()


def publish(*, policy_id: int, actor) -> AccessPolicy | None:
    """Legacy publish (TODO lane C: replace with policy_admin). Idempotent;
    returns None when the policy does not exist."""
    with transaction.atomic():
        policy = AccessPolicy.objects.select_for_update().filter(pk=policy_id).first()
        if policy is None:
            return None
        if policy.status == AccessPolicy.Status.PUBLISHED:
            return policy
        policy.status = AccessPolicy.Status.PUBLISHED
        policy.published_at = timezone.now()
        policy.save(update_fields=["status", "published_at"])
        audit.record(actor=actor, action="vms.policy.published", entity=policy,
                     detail={"version": policy.version})
    return policy
