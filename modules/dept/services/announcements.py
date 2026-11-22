"""Announcement mutation services (CFR-DEPT-001, CFR-DEPT-003)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError

from modules.dept.models.announcements import Announcement
from modules.dept.models.department import Department


def create_announcement(
    department_code: str,
    author_principal: Any,
    title: str,
    content: str,
    target_role: str = "ALL",
    target_program: str = "ALL",
    target_academic_year: int | None = None,
) -> Announcement:
    if not title or not title.strip():
        raise ValidationError("Announcement title cannot be empty.")
    if not content or not content.strip():
        raise ValidationError("Announcement content cannot be empty.")

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    user_id = str(getattr(author_principal, "user_id", getattr(author_principal, "id", "system")))
    roles = getattr(author_principal, "roles", ["faculty"])
    author_role = roles[0] if roles else "faculty"

    return Announcement.objects.create(
        department=dept,
        title=title.strip(),
        content=content.strip(),
        author_id=user_id,
        author_role=author_role,
        target_role=target_role.upper() if target_role else "ALL",
        target_program=target_program.strip() if target_program else "ALL",
        target_academic_year=target_academic_year,
        status="ACTIVE",
    )


def update_announcement(
    announcement_id: str,
    principal: Any,
    title: str | None = None,
    content: str | None = None,
    status: str | None = None,
) -> Announcement:
    ann = Announcement.objects.get(id=announcement_id)

    roles = set(getattr(principal, "roles", []))
    if "HOD" not in roles and not getattr(principal, "is_staff", False):
        raise PermissionDenied(
            "Only the HOD may modify active department announcements (BR-DEPT-004)."
        )

    if title is not None:
        if not title.strip():
            raise ValidationError("Title cannot be empty.")
        ann.title = title.strip()
    if content is not None:
        if not content.strip():
            raise ValidationError("Content cannot be empty.")
        ann.content = content.strip()
    if status is not None:
        status_norm = status.upper().strip()
        if status_norm in {"ACTIVE", "HIDDEN", "DELETED"}:
            ann.status = status_norm

    ann.save()
    return ann
