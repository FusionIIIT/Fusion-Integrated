"""Transactional Course Materials writes and scheduled release handling."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import (
    CourseRole,
    MaterialStatus,
    MaterialType,
    SectionType,
    validate_material_details,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import CourseMaterial, CourseMembership
from modules.lms.services.authz import require

P_MANAGE_MATERIAL = "lms.material.manage"


@transaction.atomic
def create_course_material(
    *,
    actor,
    course_code: str,
    title: str,
    section_title: str,
    material_type: str = MaterialType.FILE,
    section_type: str = SectionType.MODULE,
    status: str = MaterialStatus.PUBLISHED,
    description: str = "",
    link_url: str = "",
    content: str = "",
    file: Any = None,
    file_name: str = "",
    file_size: int | None = None,
    release_at: datetime | None = None,
    order: int = 0,
) -> CourseMaterial:
    """Create a course material item under CFR-LMS-003.

    Strictly restricted to Faculty assigned to this course (AFR-LMS-003.1, BR-LMS-004).
    TAs, Students, and Observers are explicitly prevented from authoring course materials
    (AFR-LMS-014.2, AFR-LMS-015.4, BR-LMS-004).
    """
    require(actor, P_MANAGE_MATERIAL)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can author course materials."
        )

    # Normalize inputs
    cleaned_title = title.strip()
    cleaned_sec_title = section_title.strip()
    cleaned_url = link_url.strip() if link_url else ""
    cleaned_content = content.strip() if content else ""

    # Scheduled material check: if release time is already in the past, publish immediately
    cleaned_status = status.strip() if status else MaterialStatus.PUBLISHED
    if cleaned_status == MaterialStatus.SCHEDULED and release_at and release_at <= timezone.now():
        cleaned_status = MaterialStatus.PUBLISHED

    try:
        validate_material_details(
            title=cleaned_title,
            section_title=cleaned_sec_title,
            material_type=material_type,
            section_type=section_type,
            status=cleaned_status,
            link_url=cleaned_url,
            content=cleaned_content,
            release_at=release_at,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="lms_validation_failed") from exc

    # Compute file metadata if file is uploaded
    computed_file_name = file_name
    computed_file_size = file_size
    if file:
        if not computed_file_name and hasattr(file, "name"):
            computed_file_name = file.name
        if computed_file_size is None and hasattr(file, "size"):
            computed_file_size = file.size

    material = CourseMaterial(
        course=membership.course,
        title=cleaned_title,
        description=description.strip() if description else "",
        material_type=material_type,
        section_type=section_type,
        section_title=cleaned_sec_title,
        file=file,
        file_name=computed_file_name,
        file_size=computed_file_size,
        link_url=cleaned_url,
        content=cleaned_content,
        status=cleaned_status,
        release_at=release_at,
        order=order,
        created_by_user_id=actor.user_id,
    )
    material.save()
    return material


@transaction.atomic
def update_course_material(
    *,
    actor,
    course_code: str,
    material_id: int,
    title: str | None = None,
    section_title: str | None = None,
    material_type: str | None = None,
    section_type: str | None = None,
    status: str | None = None,
    description: str | None = None,
    link_url: str | None = None,
    content: str | None = None,
    file: Any = None,
    release_at: datetime | None = None,
    order: int | None = None,
) -> CourseMaterial:
    """Update course material details or publication status (Faculty only)."""
    require(actor, P_MANAGE_MATERIAL)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can edit course materials."
        )

    material = (
        CourseMaterial.objects.filter(course=membership.course, id=material_id)
        .first()
    )
    if material is None:
        raise NotFoundError("Course material not found.")

    new_title = title.strip() if title is not None else material.title
    new_sec_title = section_title.strip() if section_title is not None else material.section_title
    new_type = material_type if material_type is not None else material.material_type
    new_sec_type = section_type if section_type is not None else material.section_type
    new_status = status.strip() if status is not None else material.status
    new_url = link_url.strip() if link_url is not None else material.link_url
    new_content = content.strip() if content is not None else material.content
    new_release_at = release_at if release_at is not None else material.release_at

    if (
        new_status == MaterialStatus.SCHEDULED
        and new_release_at
        and new_release_at <= timezone.now()
    ):
        new_status = MaterialStatus.PUBLISHED

    try:
        validate_material_details(
            title=new_title,
            section_title=new_sec_title,
            material_type=new_type,
            section_type=new_sec_type,
            status=new_status,
            link_url=new_url,
            content=new_content,
            release_at=new_release_at,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="lms_validation_failed") from exc

    material.title = new_title
    material.section_title = new_sec_title
    material.material_type = new_type
    material.section_type = new_sec_type
    material.status = new_status
    material.link_url = new_url
    material.content = new_content
    material.release_at = new_release_at

    if description is not None:
        material.description = description.strip()
    if order is not None:
        material.order = order

    if file:
        material.file = file
        if hasattr(file, "name"):
            material.file_name = file.name
        if hasattr(file, "size"):
            material.file_size = file.size

    material.save()
    return material


@transaction.atomic
def delete_course_material(
    *, actor, course_code: str, material_id: int
) -> None:
    """Delete a course material item (Faculty only)."""
    require(actor, P_MANAGE_MATERIAL)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can delete course materials."
        )

    material = (
        CourseMaterial.objects.filter(course=membership.course, id=material_id)
        .first()
    )
    if material is None:
        raise NotFoundError("Course material not found.")

    material.delete()


@transaction.atomic
def release_scheduled_materials(*, as_of: datetime | None = None) -> int:
    """Transition scheduled materials to published state once release time is reached.

    Implements UC-LMS-015 and BW-LMS-01 state transition logic.
    """
    cutoff = as_of or timezone.now()
    scheduled = CourseMaterial.objects.filter(
        status=MaterialStatus.SCHEDULED,
        release_at__lte=cutoff,
    )
    return scheduled.update(status=MaterialStatus.PUBLISHED, updated_at=cutoff)
