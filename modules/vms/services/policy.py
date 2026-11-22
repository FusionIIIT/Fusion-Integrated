"""Access policy versioning and management services."""

from __future__ import annotations

from datetime import time

from django.db import transaction
from django.utils import timezone

from modules.vms.models import AccessPolicy


@transaction.atomic
def create_access_policy(
    version: int,
    visiting_hours_start: time = time(8, 0),
    visiting_hours_end: time = time(20, 0),
    max_duration_hours: int = 12,
    policy_notes: str = "",
) -> AccessPolicy:
    """Admin creates a new version of access policy (UC-005, BR-125, BR-128)."""
    return AccessPolicy.objects.create(
        version=version,
        visiting_hours_start=visiting_hours_start,
        visiting_hours_end=visiting_hours_end,
        max_duration_hours=max_duration_hours,
        policy_notes=policy_notes,
        is_published=False,
    )


@transaction.atomic
def publish_access_policy(version: int) -> AccessPolicy:
    """Publish policy version and unpublish older active versions (BR-126, BR-127)."""
    now = timezone.now()
    # Unpublish previous
    AccessPolicy.objects.filter(is_published=True).update(is_published=False)

    policy = AccessPolicy.objects.select_for_update().get(version=version)
    policy.is_published = True
    policy.published_at = now
    policy.save(update_fields=["is_published", "published_at", "updated_at"])
    return policy
