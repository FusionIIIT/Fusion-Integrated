"""UC-DEPT-002 Create Announcement, UC-DEPT-003 Manage Active Announcement."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.dept.domain.visibility import validate_publication
from modules.dept.models import Announcement
from modules.dept.services._errors import require, translated


@transaction.atomic
def publish(*, actor, title: str, body: str, target_roles=(),
            target_programmes=(), target_years=()) -> Announcement:
    require(actor, "dept.announcement.publish")                  # BR-DEPT-001
    roles, programmes, years = (list(target_roles), list(target_programmes),
                                list(target_years))
    with translated():
        validate_publication(title, body, roles, programmes, years)  # BR-DEPT-003
    return Announcement.objects.create(
        title=title.strip(), body=body, target_roles=roles,
        target_programmes=programmes, target_years=years,
        published_by_user_id=actor.user_id,
        published_by_role=actor.active_role or "")


def _lock_active(announcement_id: int) -> Announcement:
    announcement = (Announcement.objects.select_for_update()
                    .filter(pk=announcement_id).first())
    if announcement is None or announcement.status == Announcement.DELETED:
        raise NotFoundError("No such announcement.")
    return announcement


@transaction.atomic
def edit(*, announcement_id: int, actor, **changes) -> Announcement:
    """BR-DEPT-004: HOD only."""
    require(actor, "dept.announcement.manage")
    announcement = _lock_active(announcement_id)
    merged = {
        "title": changes.get("title", announcement.title),
        "body": changes.get("body", announcement.body),
        "target_roles": list(changes.get("target_roles",
                                         announcement.target_roles)),
        "target_programmes": list(changes.get("target_programmes",
                                              announcement.target_programmes)),
        "target_years": list(changes.get("target_years",
                                         announcement.target_years)),
    }
    with translated():
        validate_publication(merged["title"], merged["body"],
                             merged["target_roles"],
                             merged["target_programmes"],
                             merged["target_years"])
    for field, value in merged.items():
        setattr(announcement, field, value)
    announcement.moderated_by_user_id = actor.user_id
    announcement.save()
    return announcement


@transaction.atomic
def set_status(*, announcement_id: int, actor, status: str) -> Announcement:
    """Hide, unhide (re-activate) or delete. Delete is a soft delete."""
    require(actor, "dept.announcement.manage")
    if status not in (Announcement.ACTIVE, Announcement.HIDDEN,
                      Announcement.DELETED):
        raise ConflictError("Status must be active, hidden or deleted.",
                            code="bad_status")
    announcement = _lock_active(announcement_id)
    announcement.status = status
    announcement.moderated_by_user_id = actor.user_id
    announcement.save(update_fields=["status", "moderated_by_user_id",
                                     "updated_at"])
    return announcement
