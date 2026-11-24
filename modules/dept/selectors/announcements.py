"""Announcement selectors and visibility filtering (BR-DEPT-002, CFR-DEPT-002)."""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet

from modules.dept.models.announcements import Announcement


def list_announcements_for_principal(
    department_code: str,
    principal: Any,
    program: str | None = None,
    academic_year: int | None = None,
) -> QuerySet[Announcement]:
    """Return active announcements relevant to the viewer's role and cohort."""
    qs = Announcement.objects.filter(department_id=department_code, status="ACTIVE")

    # If HOD, allow viewing HIDDEN announcements as well
    roles = set(getattr(principal, "roles", []))
    is_hod = "HOD" in roles or getattr(principal, "is_staff", False)

    if is_hod:
        qs = Announcement.objects.filter(department_id=department_code).exclude(status="DELETED")
        return qs.order_by("-created_at")

    # Filter by target role
    role_filter = Q(target_role="ALL")
    if "student" in roles:
        role_filter |= Q(target_role="STUDENT")
    if "faculty" in roles:
        role_filter |= Q(target_role="FACULTY")
    if "Dept_Admin" in roles:
        role_filter |= Q(target_role="DEPT_ADMIN")

    qs = qs.filter(role_filter)

    # Filter by program if specified
    if program:
        qs = qs.filter(Q(target_program="ALL") | Q(target_program__iexact=program))

    # Filter by academic year if specified
    if academic_year:
        qs = qs.filter(Q(target_academic_year__isnull=True) | Q(target_academic_year=academic_year))

    return qs.order_by("-created_at")
