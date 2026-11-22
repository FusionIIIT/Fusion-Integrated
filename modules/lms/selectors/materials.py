"""Course material selectors."""

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.utils import timezone

from modules.lms.domain.constants import MaterialStatus
from modules.lms.models import CourseMaterial
from modules.lms.selectors.scoping import (
    has_course_access,
    is_course_instructor,
    is_course_ta,
)


def list_published_materials(course_id: int, principal: Any) -> list[CourseMaterial]:
    if not has_course_access(course_id, principal):
        return []

    is_staff = is_course_instructor(course_id, principal) or is_course_ta(course_id, principal)

    qs = CourseMaterial.objects.filter(course_id=course_id)
    if is_staff:
        return list(
            qs.exclude(status=MaterialStatus.ARCHIVED).order_by(
                "section_name", "sort_order", "-created_at"
            )
        )

    # Student and Observer view: strictly published and release_date reached.
    now = timezone.now()
    return list(
        qs.filter(
            status=MaterialStatus.PUBLISHED,
        )
        .filter(Q(release_date__isnull=True) | Q(release_date__lte=now))
        .order_by("section_name", "sort_order", "-created_at")
    )


def get_material_detail(material_id: int, principal: Any) -> CourseMaterial | None:
    material = CourseMaterial.objects.filter(id=material_id).first()
    if not material or not has_course_access(material.course_id, principal):
        return None

    is_staff = is_course_instructor(material.course_id, principal) or is_course_ta(
        material.course_id, principal
    )
    if is_staff:
        return material

    now = timezone.now()
    if material.status == MaterialStatus.PUBLISHED and (
        material.release_date is None or material.release_date <= now
    ):
        return material
    return None
