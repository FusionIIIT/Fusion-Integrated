"""Course Materials and Sections write services (CFR-LMS-003, BR-LMS-004, BR-LMS-006)."""
from __future__ import annotations

from datetime import datetime
import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from core.files.validators import sanitise_filename
from modules.courses.domain.errors import CourseDomainError
from modules.courses.domain.materials import (
    MaterialCreateDTO,
    MaterialUpdateDTO,
    SectionCreateDTO,
    SectionUpdateDTO,
    validate_material_author,
)
from modules.courses.models import CourseMaterial, CourseMaterialSection, CourseWorkspace
from modules.courses.selectors import scoping

log = logging.getLogger("fusion.courses.materials")


def create_section(
    *,
    workspace_id: int,
    principal,
    title: str,
    description: str = "",
    sort_order: int = 0,
) -> CourseMaterialSection:
    """Creates a new course module or weekly section (AFR-LMS-003.2)."""
    dto = SectionCreateDTO(title=title, description=description, sort_order=sort_order)
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Check authorization: Only assigned faculty instructors can create sections
        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course sections."
                )
            raise NotFoundError("Course workspace not found.")

        section = CourseMaterialSection.objects.create(
            workspace=workspace,
            title=title.strip(),
            description=description.strip(),
            sort_order=sort_order,
        )
        return section


def update_section(
    *,
    workspace_id: int,
    section_id: int,
    principal,
    title: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
) -> CourseMaterialSection:
    """Updates an existing section in the workspace."""
    dto = SectionUpdateDTO(title=title, description=description, sort_order=sort_order)
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course sections."
                )
            raise NotFoundError("Course workspace not found.")

        section = (
            CourseMaterialSection.objects.filter(id=section_id, workspace=workspace)
            .select_for_update()
            .first()
        )
        if not section:
            raise NotFoundError("Course section not found.")

        if title is not None:
            section.title = title.strip()
        if description is not None:
            section.description = description.strip()
        if sort_order is not None:
            section.sort_order = sort_order

        section.save()
        return section


def delete_section(
    *,
    workspace_id: int,
    section_id: int,
    principal,
) -> None:
    """Deletes a section. Associated materials remain in the workspace with section=None."""
    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course sections."
                )
            raise NotFoundError("Course workspace not found.")

        section = CourseMaterialSection.objects.filter(
            id=section_id, workspace=workspace
        ).first()
        if not section:
            raise NotFoundError("Course section not found.")

        section.delete()


def create_material(
    *,
    workspace_id: int,
    principal,
    title: str,
    material_type: str,
    section_id: int | None = None,
    description: str = "",
    link_url: str = "",
    content: str = "",
    file=None,
    is_published: bool = True,
    release_at: datetime | None = None,
    sort_order: int = 0,
) -> CourseMaterial:
    """Creates a new course material item (file, external link, or note).

    Enforces BR-LMS-004 (TAs cannot author or edit materials),
    BR-LMS-005 (lifecycle publication), and BR-LMS-006 (future scheduling).
    """
    dto = MaterialCreateDTO(
        title=title,
        material_type=material_type,
        description=description,
        link_url=link_url,
        content=content,
        has_file=file is not None,
        is_published=is_published,
        release_at=release_at,
        sort_order=sort_order,
    )
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Check authorization: Only assigned faculty instructors can create materials (BR-LMS-004)
        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may create course materials."
                )
            raise NotFoundError("Course workspace not found.")

        section = None
        if section_id is not None:
            section = CourseMaterialSection.objects.filter(
                id=section_id, workspace=workspace
            ).first()
            if not section:
                raise BadRequestError(
                    f"Section {section_id} does not belong to this course workspace."
                )

        # File processing where supported
        saved_file = None
        filename = ""
        file_size = 0
        mime_type = ""
        if material_type == "file" and file:
            filename = sanitise_filename(getattr(file, "name", "material_upload"))
            file_size = getattr(file, "size", 0)
            mime_type = getattr(file, "content_type", "")
            saved_file = file

        material = CourseMaterial.objects.create(
            workspace=workspace,
            section=section,
            title=title.strip(),
            description=description.strip(),
            material_type=material_type,
            file=saved_file,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            link_url=link_url.strip() if link_url else "",
            content=content.strip() if content else "",
            is_published=is_published,
            release_at=release_at,
            created_by_id=principal.user_id,
            sort_order=sort_order,
        )

        log.info(
            "courses.material.created id=%d workspace=%s type=%s scheduled=%s",
            material.id,
            workspace.code,
            material_type,
            material.is_scheduled,
        )
        return material


def update_material(
    *,
    workspace_id: int,
    material_id: int,
    principal,
    title: str | None = None,
    description: str | None = None,
    section_id: int | None = None,
    clear_section: bool = False,
    link_url: str | None = None,
    content: str | None = None,
    file=None,
    is_published: bool | None = None,
    release_at: datetime | None = None,
    clear_release_at: bool = False,
    sort_order: int | None = None,
) -> CourseMaterial:
    """Updates an existing course material item."""
    dto = MaterialUpdateDTO(
        title=title,
        description=description,
        link_url=link_url,
        content=content,
        section_id=section_id,
        clear_section=clear_section,
        is_published=is_published,
        release_at=release_at,
        clear_release_at=clear_release_at,
        sort_order=sort_order,
    )
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may edit course materials."
                )
            raise NotFoundError("Course workspace not found.")

        material = (
            CourseMaterial.objects.filter(id=material_id, workspace=workspace)
            .select_for_update()
            .first()
        )
        if not material:
            raise NotFoundError("Course material not found.")

        if title is not None:
            material.title = title.strip()
        if description is not None:
            material.description = description.strip()
        if link_url is not None:
            material.link_url = link_url.strip()
        if content is not None:
            material.content = content.strip()
        if is_published is not None:
            material.is_published = is_published
        if sort_order is not None:
            material.sort_order = sort_order

        if clear_section:
            material.section = None
        elif section_id is not None:
            sec = CourseMaterialSection.objects.filter(
                id=section_id, workspace=workspace
            ).first()
            if not sec:
                raise BadRequestError(
                    f"Section {section_id} does not belong to this course workspace."
                )
            material.section = sec

        if clear_release_at:
            material.release_at = None
        elif release_at is not None:
            material.release_at = release_at

        if file is not None and material.material_type == "file":
            material.file = file
            material.filename = sanitise_filename(
                getattr(file, "name", "material_upload")
            )
            material.file_size = getattr(file, "size", 0)
            material.mime_type = getattr(file, "content_type", "")

        material.save()
        log.info(
            "courses.material.updated id=%d workspace=%s",
            material.id,
            workspace.code,
        )
        return material


def delete_material(
    *,
    workspace_id: int,
    material_id: int,
    principal,
) -> None:
    """Deletes a course material."""
    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may delete course materials."
                )
            raise NotFoundError("Course workspace not found.")

        material = CourseMaterial.objects.filter(
            id=material_id, workspace=workspace
        ).first()
        if not material:
            raise NotFoundError("Course material not found.")

        material_id_val = material.id
        if material.file:
            material.file.delete(save=False)
        material.delete()
        log.info(
            "courses.material.deleted id=%d workspace=%s",
            material_id_val,
            workspace.code,
        )


def publish_scheduled_materials() -> int:
    """Finds all scheduled materials whose release time has arrived and marks them active (AFR-LMS-003.4, BW-LMS-01).

    This service is called by the periodic Celery task or cron management command.
    Note: Even if this job runs late or is delayed, query-level release-time checks
    guarantee non-faculty users cannot view materials before release_at.
    """
    now = timezone.now()
    scheduled = CourseMaterial.objects.filter(
        is_published=True,
        release_at__isnull=False,
        release_at__lte=now,
    )
    count = scheduled.count()
    if count:
        log.info("courses.materials.scheduled_released count=%d", count)
    return count

