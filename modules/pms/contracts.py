"""PMS public surface for other Fusion modules. Plural by signature (ADR-0010)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PatentPortfolioDTO:
    user_id: int
    application_count: int
    granted_count: int
    has_active_patents: bool


def get_patent_portfolios(user_ids: Sequence[int]) -> dict[int, PatentPortfolioDTO]:
    """Retrieve summarized patent portfolio stats for a batch of users."""
    from modules.pms.models import PatentApplication

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    apps = PatentApplication.objects.filter(user_id__in=ids)
    app_counts: dict[int, int] = {}
    granted_counts: dict[int, int] = {}

    for app in apps:
        app_counts[app.user_id] = app_counts.get(app.user_id, 0) + 1
        if app.status == "granted":
            granted_counts[app.user_id] = granted_counts.get(app.user_id, 0) + 1

    return {
        uid: PatentPortfolioDTO(
            user_id=uid,
            application_count=app_counts.get(uid, 0),
            granted_count=granted_counts.get(uid, 0),
            has_active_patents=app_counts.get(uid, 0) > 0,
        )
        for uid in ids
    }


@dataclass(frozen=True)
class PatentClearanceDTO:
    user_id: int
    has_pending_obligations: bool
    pending_count: int
    message: str


def get_patent_clearances(user_ids: Sequence[int]) -> dict[int, PatentClearanceDTO]:
    """Check whether graduating students or departing faculty have pending patent actions."""
    from modules.pms.models import PatentApplication

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    pending_statuses = {"needs_revision", "awaiting_applicant_approval"}
    pending_apps = PatentApplication.objects.filter(
        user_id__in=ids, status__in=pending_statuses
    ).values_list("user_id", flat=True)

    counts: dict[int, int] = {}
    for uid in pending_apps:
        counts[uid] = counts.get(uid, 0) + 1

    return {
        uid: PatentClearanceDTO(
            user_id=uid,
            has_pending_obligations=counts.get(uid, 0) > 0,
            pending_count=counts.get(uid, 0),
            message=(
                f"{counts[uid]} patent action(s) require applicant response."
                if counts.get(uid, 0) > 0
                else "No pending patent obligations."
            ),
        )
        for uid in ids
    }
