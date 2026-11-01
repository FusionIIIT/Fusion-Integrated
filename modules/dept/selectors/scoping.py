"""Who sees what. Every view reads through here, so authorisation is derived
once; anything out of scope is absent, which is why detail views 404."""
from __future__ import annotations

from modules.dept.domain import state_machine as sm
from modules.dept.domain.visibility import Viewer, is_visible
from modules.dept.models import (
    Announcement,
    Feedback,
    InventoryItem,
    StockMovement,
    StockRequest,
)
from modules.directory import contracts as directory

MAX_ANNOUNCEMENTS = 200


def viewer_for(principal) -> Viewer:
    """Programme and batch year come from the directory, not the session."""
    user = directory.get_users([principal.user_id]).get(principal.user_id)
    role = principal.kind if principal.kind in ("student", "faculty") else "staff"
    if user is None:
        return Viewer(role=role)
    return Viewer(role=role, programme=user.programme, batch_year=user.batch_year)


def announcements_for(principal) -> list[Announcement]:
    """BR-DEPT-002. Moderators (HOD) see everything but deleted ones, hidden
    included; managers of the department see all active notices; everyone else
    only what targets them."""
    qs = Announcement.objects.order_by("-created_at")
    if principal.has_permission("dept.announcement.manage"):
        return list(qs.exclude(status=Announcement.DELETED)[:MAX_ANNOUNCEMENTS])

    rows = qs.filter(status=Announcement.ACTIVE)[:MAX_ANNOUNCEMENTS]
    if principal.has_permission("dept.inventory.manage"):    # Dept_Admin
        return list(rows)
    viewer = viewer_for(principal)
    return [a for a in rows if is_visible(
        roles=a.target_roles, programmes=a.target_programmes,
        years=a.target_years, viewer=viewer)
        or a.published_by_user_id == principal.user_id]


def inventory():
    return InventoryItem.objects.order_by("name")


def stock_requests_for(principal):
    qs = StockRequest.objects.select_related("item").order_by("-created_at")
    if principal.has_permission("dept.stock_request.view_all"):
        return qs
    return qs.filter(requested_by_user_id=principal.user_id)


def issued_history_for(principal):
    """FR: Faculty see the issued-stock history that concerns them."""
    return stock_requests_for(principal).filter(status=sm.ISSUED)


def stock_log():
    return StockMovement.objects.select_related("item").order_by("-at", "-id")


def feedback_for(principal):
    """BR-DEPT-017: the submitter, Dept_Admin, and — only once the initial
    review is done (BR-DEPT-018) — the HOD."""
    qs = Feedback.objects.order_by("-created_at")
    if principal.has_permission("dept.feedback.review"):
        return qs
    if principal.has_permission("dept.feedback.resolve"):
        return qs.exclude(status=sm.NEW)
    return qs.filter(submitted_by_user_id=principal.user_id)
