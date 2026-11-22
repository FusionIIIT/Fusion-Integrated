"""Project selectors for RSPC."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.rspc.models import Project
from modules.rspc.selectors.scoping import scope_projects


def list_projects(request, status: str | None = None) -> QuerySet[Project]:
    qs = scope_projects(request).prefetch_related("budget_heads", "co_pis").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs
