"""Reporting, portfolio analytics and dashboard selectors (BR-PMS-003, 005)."""

from __future__ import annotations

from typing import Any

from django.db.models import Count

from modules.pms.selectors.scoping import scoped_applications


def get_portfolio_summary_stats(actor) -> dict[str, Any]:
    """Calculate aggregated portfolio statistics within the actor's authorized scope."""
    qs = scoped_applications(actor)

    total_count = qs.count()
    status_counts = dict(
        qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    domain_counts = dict(
        qs.values("domain").annotate(count=Count("id")).values_list("domain", "count")
    )

    return {
        "total_applications": total_count,
        "granted_count": status_counts.get("granted", 0),
        "in_review_count": status_counts.get("under_review", 0),
        "filed_count": status_counts.get("filed", 0),
        "needs_revision_count": status_counts.get("needs_revision", 0),
        "status_distribution": status_counts,
        "domain_distribution": domain_counts,
    }
