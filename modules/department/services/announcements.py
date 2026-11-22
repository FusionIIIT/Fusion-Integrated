"""UC-DEPT-002 publish and UC-DEPT-003 maintain announcements."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.department.domain import rules
from modules.department.domain.roles import ActorContext
from modules.department.models import Announcement
from modules.department.selectors import scoping
from modules.department.services import notifications
from modules.department.services.common import get_scoped, own_department, translated


@transaction.atomic
def publish(
    ctx: ActorContext,
    *,
    title: str,
    body: str,
    audience_role: str,
    programme: str = "",
    batch_year: int | None = None,
) -> Announcement:
    """BR-DEPT-001 by permission, BR-DEPT-003 here, AFR-DEPT-046 in the same transaction."""
    dept = own_department(ctx)
    with translated():
        rules.validate_announcement(
            title=title,
            body=body,
            audience_role=audience_role,
            programme=programme,
            batch_year=batch_year,
        )
    ann = Announcement.objects.create(
        department=dept,
        title=title.strip(),
        body=body.strip(),
        audience_role=audience_role,
        programme=programme or "",
        batch_year=batch_year,
        author_id=ctx.user_id,
        published_at=timezone.now(),
    )
    recipients = notifications.announcement_audience(
        department_code=dept.code,
        audience_role=audience_role,
        programme=ann.programme,
        batch_year=batch_year,
    )
    notifications.enqueue(
        topic="announcement.published",
        recipients=recipients,
        key=str(ann.pk),
        subject=f"[{dept.code}] {ann.title}",
        body=ann.body,
    )
    return ann


def _active(ctx: ActorContext, pk: int) -> Announcement:
    ann = get_scoped(scoping.announcements_for(ctx), pk, lock=True, what="announcement")
    if ann.status != Announcement.ACTIVE:
        raise ConflictError(
            "Only an active announcement can be changed.", code="announcement_not_active"
        )
    return ann


@transaction.atomic
def edit(ctx: ActorContext, pk: int, **changes) -> Announcement:
    """AFR-DEPT-004, re-validated under BR-DEPT-003."""
    ann = _active(ctx, pk)
    merged = {
        f: changes.get(f, getattr(ann, f))
        for f in ("title", "body", "audience_role", "programme", "batch_year")
    }
    with translated():
        rules.validate_announcement(**merged)
    for field, value in merged.items():
        setattr(ann, field, value.strip() if isinstance(value, str) else value)
    ann.edited_by, ann.edited_at = ctx.user_id, timezone.now()
    ann.save()
    return ann


@transaction.atomic
def hide(ctx: ActorContext, pk: int) -> Announcement:
    """AFR-DEPT-005."""
    ann = _active(ctx, pk)
    ann.status, ann.edited_by, ann.edited_at = Announcement.HIDDEN, ctx.user_id, timezone.now()
    ann.save(update_fields=["status", "edited_by", "edited_at", "updated_at"])
    return ann


@transaction.atomic
def delete(ctx: ActorContext, pk: int) -> None:
    """AFR-DEPT-006 with Q7: soft delete, kept for audit, gone from every view."""
    ann = _active(ctx, pk)
    ann.status, ann.edited_by, ann.edited_at = Announcement.DELETED, ctx.user_id, timezone.now()
    ann.save(update_fields=["status", "edited_by", "edited_at", "updated_at"])
