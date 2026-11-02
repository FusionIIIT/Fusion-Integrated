"""Access policy drafts and publication (VMS-UC-006, CFR-006, BR-125..129).

Only a draft is editable (BR-128). Publishing makes a version the runtime
source (BR-125/127); older versions stay as history (BR-126). Existing requests
keep the policy that applied to them (BR-129, ``policy.snapshot_for``), so
nothing here touches a request.
"""
from __future__ import annotations

import datetime

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import AccessPolicy, Zone
from modules.vms.services.common import audit, authz

MANAGE = "vms.policy.manage"
PUBLISH = "vms.policy.publish"

#: Scalar fields an admin may edit; restricted_zones is handled separately.
FIELDS = (
    "visiting_hours_start", "visiting_hours_end", "max_visit_hours",
    "walk_in_pass_hours", "approval_timeout_hours", "reminder_after_hours",
    "advance_registration_hours", "allow_same_day_urgent",
    "contingency_sla_minutes", "walkin_rate_limit_per_hour",
)
_POSITIVE = ("max_visit_hours", "walk_in_pass_hours", "approval_timeout_hours",
             "reminder_after_hours", "contingency_sla_minutes",
             "walkin_rate_limit_per_hour")


def validate(values: dict) -> list[dict]:
    """Return a list of {field, message} problems for a full set of values."""
    errs = []

    def bad(field, msg):
        errs.append({"field": field, "message": msg})

    for f in _POSITIVE:
        if not isinstance(values[f], int) or values[f] <= 0:
            bad(f, "must be a positive whole number")
    if not isinstance(values["advance_registration_hours"], int) \
            or values["advance_registration_hours"] < 0:
        bad("advance_registration_hours", "must be zero or more")
    start, end = values["visiting_hours_start"], values["visiting_hours_end"]
    if not (isinstance(start, datetime.time) and isinstance(end, datetime.time)):
        bad("visiting_hours_start", "visiting hours must be times")
    elif start >= end:
        bad("visiting_hours_end", "must be after visiting_hours_start")
    if not errs:
        if values["walk_in_pass_hours"] > values["max_visit_hours"]:
            bad("walk_in_pass_hours", "must not exceed max_visit_hours")
        if values["max_visit_hours"] > 24:
            bad("max_visit_hours", "must not exceed 24")
        if values["reminder_after_hours"] >= values["approval_timeout_hours"]:
            bad("reminder_after_hours", "must be before approval_timeout_hours")
    return errs


def _values(policy: AccessPolicy) -> dict:
    return {f: getattr(policy, f) for f in FIELDS}


def _raise(errs):
    raise BadRequestError("The policy values are inconsistent.",
                          code="validation_error", details=errs)


def get(policy_id: int) -> AccessPolicy:
    p = AccessPolicy.objects.filter(pk=policy_id).first()
    if p is None:
        raise NotFoundError("Policy not found.")
    return p


def list_policies(*, actor):
    if not actor.has_any_permission(MANAGE, PUBLISH):
        authz.require(actor, MANAGE)
    return AccessPolicy.objects.order_by("-version")


def create_draft(*, actor, base_id: int | None = None) -> AccessPolicy:
    """A new draft copied from `base_id`, else from the latest published
    policy, else from the model defaults (BR-128). One open draft at a time."""
    authz.require(actor, MANAGE)
    with transaction.atomic():
        # Lock the newest row so concurrent creators serialise on the version number.
        latest = AccessPolicy.objects.select_for_update().order_by("-version").first()
        if AccessPolicy.objects.filter(status=AccessPolicy.Status.DRAFT).exists():
            raise ConflictError("A draft policy already exists; edit or publish it first.",
                                code="draft_exists")
        if base_id is not None:
            base = AccessPolicy.objects.filter(pk=base_id).first()
            if base is None:
                raise NotFoundError("Base policy not found.")
        else:
            base = (AccessPolicy.objects.filter(status=AccessPolicy.Status.PUBLISHED)
                    .order_by("-version").first())
        version = (latest.version if latest else 0) + 1
        draft = AccessPolicy.objects.create(
            version=version, status=AccessPolicy.Status.DRAFT,
            created_by_user_id=actor.user_id, **(_values(base) if base else {}))
        if base:
            draft.restricted_zones.set(base.restricted_zones.all())
        audit.record(actor=actor, action="vms.policy.draft_created", entity=draft,
                     detail={"version": version, "base_version": base.version if base else None})
    return draft


def update_draft(*, actor, policy_id: int, changes: dict,
                 restricted_zone_ids=None) -> AccessPolicy:
    authz.require(actor, MANAGE)
    unknown = sorted(set(changes) - set(FIELDS))
    if unknown:
        raise BadRequestError(f"Unknown field(s): {', '.join(unknown)}.",
                              code="validation_error")
    with transaction.atomic():
        policy = AccessPolicy.objects.select_for_update().filter(pk=policy_id).first()
        if policy is None:
            raise NotFoundError("Policy not found.")
        if policy.status != AccessPolicy.Status.DRAFT:       # BR-128
            raise ConflictError("Only a draft can be edited; create a new draft.",
                                code="not_a_draft")
        merged = {**_values(policy), **changes}
        errs = validate(merged)
        if errs:
            _raise(errs)
        zones = None
        if restricted_zone_ids is not None:
            zones = list(Zone.objects.filter(pk__in=set(restricted_zone_ids)))
            if len(zones) != len(set(restricted_zone_ids)):
                raise BadRequestError("Unknown zone.", code="unknown_zone")
        before = _values(policy)
        for f, v in changes.items():
            setattr(policy, f, v)
        policy.save()
        if zones is not None:
            policy.restricted_zones.set(zones)
        changed = {f: [str(before[f]), str(merged[f])] for f in changes
                   if before[f] != merged[f]}
        audit.record(actor=actor, action="vms.policy.draft_updated", entity=policy,
                     detail={"version": policy.version, "changed": changed,
                             "restricted_zones_set": zones is not None})
    return policy


def publish(*, actor, policy_id: int) -> AccessPolicy:
    """Atomically make the draft the runtime source (BR-125/127)."""
    authz.require(actor, PUBLISH)
    with transaction.atomic():
        policy = AccessPolicy.objects.select_for_update().filter(pk=policy_id).first()
        if policy is None:
            raise NotFoundError("Policy not found.")
        if policy.status != AccessPolicy.Status.DRAFT:
            raise ConflictError("Only a draft can be published.", code="not_a_draft")
        errs = validate(_values(policy))
        if errs:
            _raise(errs)
        newest = AccessPolicy.objects.filter(
            status=AccessPolicy.Status.PUBLISHED).aggregate(m=Max("version"))["m"] or 0
        if policy.version < newest:
            raise ConflictError("A newer version is already published.",
                                code="stale_draft")
        policy.status = AccessPolicy.Status.PUBLISHED
        policy.published_at = timezone.now()
        policy.save(update_fields=["status", "published_at"])
        audit.record(actor=actor, action="vms.policy.published", entity=policy,
                     detail={"version": policy.version})
    return policy


def diff(*, actor, a_id: int, b_id: int) -> dict:
    """Field-by-field difference between two versions, `a` to `b`."""
    if not actor.has_any_permission(MANAGE, PUBLISH):
        authz.require(actor, MANAGE)
    a, b = get(a_id), get(b_id)
    changes = {}
    for f in FIELDS:
        if getattr(a, f) != getattr(b, f):
            changes[f] = {"a": getattr(a, f), "b": getattr(b, f)}
    za = sorted(a.restricted_zones.values_list("pk", flat=True))
    zb = sorted(b.restricted_zones.values_list("pk", flat=True))
    if za != zb:
        changes["restricted_zones"] = {"a": za, "b": zb}
    return {"a": a.version, "b": b.version, "changes": changes}
