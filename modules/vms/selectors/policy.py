"""Read-only selectors for access policy."""

from __future__ import annotations

from modules.vms.models import AccessPolicy


def get_active_published_policy() -> AccessPolicy | None:
    return AccessPolicy.objects.filter(is_published=True).order_by("-version").first()


def list_policies():
    return AccessPolicy.objects.all().order_by("-version")
