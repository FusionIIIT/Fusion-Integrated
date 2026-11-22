from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.department.models import Announcement


P_VIEW = "department.announcement.view"
P_PUBLISH = "department.announcement.publish"
P_MANAGE = "department.announcement.manage"


def _require_permission(actor, permission: str) -> None:
    if actor is None or not actor.has_permission(permission):
        raise PermissionDeniedError(
            f"This action requires the {permission} permission.",
            code="permission_denied",
        )

def _require_hod(actor) -> None:
    _require_permission(actor, P_MANAGE)

    if getattr(actor, "active_role", None) != "HOD":
        raise PermissionDeniedError(
            "Only the HOD can hide or delete announcements.",
            code="permission_denied",
        )


def _validate_content(title: str, body: str) -> tuple[str, str]:
    title = (title or "").strip()
    body = (body or "").strip()

    if not title or not body:
        raise ConflictError(
            "An announcement requires a title and body.",
            code="content_required",
        )

    return title, body


def _validate_targets(
    target_roles: list[str],
    target_programs: list[str],
    target_academic_years: list[str],
) -> None:
    targets = {
        "target_roles": target_roles,
        "target_programs": target_programs,
        "target_academic_years": target_academic_years,
    }

    for field, value in targets.items():
        if not isinstance(value, list):
            raise ConflictError(
                f"{field} must be a list.",
                code="invalid_audience",
            )

        if not value or any(
            not isinstance(item, str) or not item.strip()
            for item in value
        ):
            raise ConflictError(
                f"{field} must contain at least one non-empty string.",
                code="invalid_audience",
            )


@transaction.atomic
def create_draft(*, actor, title: str, body: str) -> Announcement:
    _require_permission(actor, P_PUBLISH)
    title, body = _validate_content(title, body)

    return Announcement.objects.create(
        title=title,
        body=body,
    )


@transaction.atomic
def publish(
    *,
    announcement_id: int,
    actor,
    target_roles: list[str],
    target_programs: list[str],
    target_academic_years: list[str],
) -> Announcement:
    _require_permission(actor, P_PUBLISH)

    _validate_targets(
        target_roles,
        target_programs,
        target_academic_years,
    )

    announcement = (
        Announcement.objects.select_for_update()
        .filter(pk=announcement_id, deleted_at__isnull=True)
        .first()
    )

    if announcement is None:
        raise NotFoundError("Announcement not found.")

    if announcement.published_at is not None:
        raise ConflictError(
            "This announcement has already been published.",
            code="already_published",
        )

    announcement.target_roles = target_roles
    announcement.target_programs = target_programs
    announcement.target_academic_years = target_academic_years
    announcement.published_at = timezone.now()
    announcement.published_by_user_id = actor.user_id
    announcement.published_by_role = actor.active_role or ""

    announcement.full_clean()
    announcement.save()

    return announcement


@transaction.atomic
def hide(*, announcement_id: int, actor) -> Announcement:
    _require_hod(actor)

    announcement = (
        Announcement.objects.select_for_update()
        .filter(pk=announcement_id, deleted_at__isnull=True)
        .first()
    )

    if announcement is None:
        raise NotFoundError("Announcement not found.")

    announcement.is_hidden = True
    announcement.save(update_fields=["is_hidden", "updated_at"])
    return announcement


@transaction.atomic
def soft_delete(*, announcement_id: int, actor) -> Announcement:
    _require_hod(actor)

    announcement = (
        Announcement.objects.select_for_update()
        .filter(pk=announcement_id, deleted_at__isnull=True)
        .first()
    )

    if announcement is None:
        raise NotFoundError("Announcement not found.")

    announcement.deleted_at = timezone.now()
    announcement.save(update_fields=["deleted_at", "updated_at"])
    return announcement
