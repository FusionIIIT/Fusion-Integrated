"""Ownership- and membership-scoped LMS course material reads."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.db.models import Q
from django.utils import timezone

from modules.lms.domain.entities import CourseRole, MaterialStatus
from modules.lms.models import CourseMaterial, CourseMembership


def _material_to_dict(m: CourseMaterial) -> dict[str, Any]:
    return {
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "material_type": m.material_type,
        "section_type": m.section_type,
        "section_title": m.section_title,
        "file_name": m.file_name or (m.file.name if m.file else ""),
        "file_size": m.file_size,
        "has_file": bool(m.file),
        "link_url": m.link_url,
        "content": m.content,
        "status": m.status,
        "release_at": m.release_at.isoformat() if m.release_at else None,
        "order": m.order,
        "created_by_user_id": m.created_by_user_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def list_course_materials(*, principal, course_code: str) -> dict[str, Any] | None:
    """List course materials according to CFR-LMS-003, CFR-LMS-004, and BR-LMS-005.

    Faculty sees all materials (draft, scheduled, published) with management capabilities.
    Students, TAs, and Observers strictly see published or released materials only;
    drafts and future-scheduled materials are never exposed (BR-LMS-005, BR-LMS-006).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    now = timezone.now()
    qs = CourseMaterial.objects.filter(course=membership.course)

    if membership.role != CourseRole.FACULTY:
        # Students, TAs, Observers: Only published or released scheduled materials
        qs = qs.filter(
            Q(status=MaterialStatus.PUBLISHED)
            | Q(status=MaterialStatus.SCHEDULED, release_at__lte=now)
        )

    materials = list(qs.order_by("section_title", "order", "-created_at"))

    sections_map = defaultdict(lambda: {"section_type": "module", "materials": []})
    for m in materials:
        sec = sections_map[m.section_title]
        sec["section_title"] = m.section_title
        sec["section_type"] = m.section_type
        sec["materials"].append(_material_to_dict(m))

    sections_list = [
        {
            "section_title": sec_title,
            "section_type": sec_data["section_type"],
            "materials": sec_data["materials"],
        }
        for sec_title, sec_data in sections_map.items()
    ]

    can_manage = bool(
        membership.role == CourseRole.FACULTY
        and principal.has_permission("lms.material.manage")
    )

    return {
        "course_code": membership.course.code,
        "course_title": membership.course.title,
        "role": membership.role,
        "can_manage": can_manage,
        "sections": sections_list,
        "total_count": len(materials),
    }


def get_course_material_detail(
    *, principal, course_code: str, material_id: int
) -> dict[str, Any] | None:
    """Retrieve details for a single course material if caller has visibility."""
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    material = (
        CourseMaterial.objects.filter(course=membership.course, id=material_id)
        .first()
    )
    if material is None:
        return None

    # Visibility check for non-faculty
    if membership.role != CourseRole.FACULTY:
        now = timezone.now()
        is_accessible = (
            material.status == MaterialStatus.PUBLISHED
            or (
                material.status == MaterialStatus.SCHEDULED
                and material.release_at
                and material.release_at <= now
            )
        )
        if not is_accessible:
            return None

    return _material_to_dict(material)


def get_material_for_download(
    *, principal, course_code: str, material_id: int
) -> CourseMaterial | None:
    """Retrieve material model instance for secure file download."""
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    material = (
        CourseMaterial.objects.filter(course=membership.course, id=material_id)
        .first()
    )
    if material is None or not material.file:
        return None

    if membership.role != CourseRole.FACULTY:
        now = timezone.now()
        is_accessible = (
            material.status == MaterialStatus.PUBLISHED
            or (
                material.status == MaterialStatus.SCHEDULED
                and material.release_at
                and material.release_at <= now
            )
        )
        if not is_accessible:
            return None

    return material
