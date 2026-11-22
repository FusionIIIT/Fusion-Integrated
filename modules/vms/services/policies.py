from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.models import (
    AccessPolicyVersion,
    AuditEvent,
    BlacklistEntry,
    RegistryVersion,
    SafeListEntry,
)


@transaction.atomic
def create_policy(*, actor_id, fields):
    version = (
        AccessPolicyVersion.objects.filter(scope_key="campus").aggregate(value=Max("version"))[
            "value"
        ]
        or 0
    ) + 1
    fields = {
        k: v
        for k, v in fields.items()
        if k
        in {
            "visiting_hours_start",
            "visiting_hours_end",
            "maximum_visit_minutes",
            "walk_in_minutes",
            "approval_timeout_minutes",
            "contingency_timeout_minutes",
            "advance_registration_minutes",
            "reminder_minutes",
            "restricted_zones",
        }
    }
    if fields.get("maximum_visit_minutes", 480) <= 0 or fields.get("walk_in_minutes", 240) <= 0:
        raise ConflictError("Visit durations must be positive.", code="invalid_policy")
    policy = AccessPolicyVersion.objects.create(
        scope_key="campus", version=version, status="draft", effective_from=timezone.now(), **fields
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="staff",
        action="policy.create",
        object_type="AccessPolicyVersion",
        object_id=str(policy.pk),
        after={"version": version},
    )
    return policy


@transaction.atomic
def publish_policy(*, policy_id, actor_id):
    policy = AccessPolicyVersion.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        raise NotFoundError("Policy version not found.")
    if policy.status != "draft":
        raise ConflictError("Only a draft policy can be published.", code="policy_not_draft")
    policy.status = "published"
    policy.effective_from = timezone.now()
    policy.published_at = timezone.now()
    policy.published_by_user_id = actor_id
    policy.save(
        update_fields=[
            "status",
            "effective_from",
            "published_at",
            "published_by_user_id",
            "updated_at",
        ]
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="staff",
        action="policy.publish",
        object_type="AccessPolicyVersion",
        object_id=str(policy.pk),
        after={"version": policy.version},
    )
    return policy


@transaction.atomic
def create_registry_version(*, actor_id):
    version = (RegistryVersion.objects.aggregate(value=Max("version"))["value"] or 0) + 1
    registry = RegistryVersion.objects.create(version=version, effective_from=timezone.now())
    # A new registry starts from the current active entries, so publishing it does
    # not accidentally erase controls omitted from the change request.
    current = RegistryVersion.objects.filter(status="published").order_by("-version").first()
    if current:
        for entry in current.blacklist_entries.filter(is_active=True):
            BlacklistEntry.objects.create(
                version=registry,
                display_name=entry.display_name,
                normalized_name=entry.normalized_name,
                identity_fingerprint=entry.identity_fingerprint,
                reason=entry.reason,
                severity=entry.severity,
                expires_at=entry.expires_at,
            )
        for entry in current.safe_list_entries.filter(is_active=True):
            SafeListEntry.objects.create(
                version=registry,
                display_name=entry.display_name,
                normalized_name=entry.normalized_name,
                identity_fingerprint=entry.identity_fingerprint,
                reason=entry.reason,
                expires_at=entry.expires_at,
            )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="staff",
        action="registry.create",
        object_type="RegistryVersion",
        object_id=str(registry.pk),
        after={"version": version},
    )
    return registry


def add_blacklist_entry(*, registry_id, actor_id, name, fingerprint, reason, expires_at=None):
    registry = RegistryVersion.objects.filter(pk=registry_id, status="draft").first()
    if registry is None:
        raise ConflictError(
            "Entries can only be added to a draft registry.", code="registry_not_draft"
        )
    normalized = " ".join(name.casefold().split())
    digest = fingerprint or ""
    if not normalized and not digest:
        raise ConflictError(
            "A normalized name or identity fingerprint is required.", code="invalid_registry_entry"
        )
    entry = BlacklistEntry.objects.create(
        version=registry,
        display_name=name[:160],
        normalized_name=normalized[:160],
        identity_fingerprint=digest,
        reason=reason[:500],
        expires_at=expires_at,
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action="registry.blacklist_add",
        object_type="BlacklistEntry",
        object_id=str(entry.pk),
        after={
            "registry_version": registry.version,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
    )
    return entry


def add_safelist_entry(*, registry_id, actor_id, name, fingerprint, reason, expires_at):
    registry = RegistryVersion.objects.filter(pk=registry_id, status="draft").first()
    if registry is None:
        raise ConflictError(
            "Entries can only be added to a draft registry.", code="registry_not_draft"
        )
    normalized = " ".join(name.casefold().split())
    digest = fingerprint or ""
    if not normalized and not digest:
        raise ConflictError(
            "A normalized name or identity fingerprint is required.", code="invalid_registry_entry"
        )
    if expires_at <= timezone.now():
        raise ConflictError(
            "Safe-list entry expiry must be in the future.", code="invalid_registry_expiry"
        )
    entry = SafeListEntry.objects.create(
        version=registry,
        display_name=name[:160],
        normalized_name=normalized[:160],
        identity_fingerprint=digest,
        reason=reason[:500],
        expires_at=expires_at,
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action="registry.safelist_add",
        object_type="SafeListEntry",
        object_id=str(entry.pk),
        after={"registry_version": registry.version, "expires_at": expires_at.isoformat()},
    )
    return entry


@transaction.atomic
def publish_registry(*, registry_id, actor_id):
    registry = RegistryVersion.objects.select_for_update().filter(pk=registry_id).first()
    if registry is None:
        raise NotFoundError("Registry version not found.")
    if registry.status != "draft":
        raise ConflictError("Only a draft registry can be published.", code="registry_not_draft")
    registry.status = "published"
    registry.effective_from = timezone.now()
    registry.published_at = timezone.now()
    registry.published_by_user_id = actor_id
    registry.save(
        update_fields=[
            "status",
            "effective_from",
            "published_at",
            "published_by_user_id",
            "updated_at",
        ]
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="staff",
        action="registry.publish",
        object_type="RegistryVersion",
        object_id=str(registry.pk),
        after={"version": registry.version},
    )
    return registry
