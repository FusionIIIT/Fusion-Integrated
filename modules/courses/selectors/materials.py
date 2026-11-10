"""Selectors for Course Materials and Sections with release and role scoping (BR-LMS-001, BR-LMS-005, BR-LMS-006)."""
from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from modules.courses.models import CourseMaterial, CourseMaterialSection, CourseWorkspace
from modules.courses.selectors import scoping


def visible_sections(
    workspace: CourseWorkspace, principal,
) -> QuerySet[CourseMaterialSection]:
    """Returns sections in the workspace visible to the actor."""
    if not principal:
        return CourseMaterialSection.objects.none()

    # Must be a member of the workspace
    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership:
        return CourseMaterialSection.objects.none()

    return CourseMaterialSection.objects.filter(workspace=workspace).order_by(
        "sort_order", "id"
    )


def visible_materials(
    workspace: CourseWorkspace, principal,
) -> QuerySet[CourseMaterial]:
    """Returns materials visible to the requesting actor.

    Faculty instructors see all materials (published, unpublished, and scheduled)
    for courses they instruct (AFR-LMS-003.1).

    Students, TAs, and Observers see ONLY materials that are:
    1. is_published = True
    2. release_at is None OR release_at <= now()
    (BR-LMS-004, BR-LMS-005, BR-LMS-006, CFR-LMS-004).

    Enforcing release-time checks in the query ensures scheduled materials are
    never exposed prior to release time, regardless of scheduler execution status.
    """
    if not principal:
        return CourseMaterial.objects.none()

    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership:
        return CourseMaterial.objects.none()

    qs = CourseMaterial.objects.filter(workspace=workspace)

    # Faculty instructors see all materials in their course
    if scoping.is_course_instructor(workspace, principal):
        return qs.order_by("sort_order", "id")

    # Non-faculty roles (students, TAs, observers): only published and released
    now = timezone.now()
    return qs.filter(
        is_published=True,
    ).filter(
        Q(release_at__isnull=True) | Q(release_at__lte=now)
    ).order_by("sort_order", "id")


def get_material_for_actor(
    workspace_id: int,
    material_id: int,
    principal,
) -> CourseMaterial | None:
    """Retrieves a single material scoped strictly to the specified workspace."""
    workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return None

    return visible_materials(workspace, principal).filter(id=material_id).first()


def get_section_for_actor(
    workspace_id: int,
    section_id: int,
    principal,
) -> CourseMaterialSection | None:
    """Retrieves a single section scoped strictly to the specified workspace."""
    workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return None

    return visible_sections(workspace, principal).filter(id=section_id).first()

