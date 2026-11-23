"""Course material management service operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from core.files.validators import sanitise_filename
from modules.lms.domain.constants import MaterialType
from modules.lms.domain.state_machine import MaterialFSM
from modules.lms.domain.validators import validate_material_payload
from modules.lms.models import CourseMaterial
from modules.lms.selectors.scoping import is_course_instructor


def _validate_file_upload(file_obj: Any) -> None:
    """Validates attachment size and sanitises its filename."""
    max_bytes = 20 * 1024 * 1024
    if file_obj.size > max_bytes:
        raise BadRequestError("File size cannot exceed 20 MB; compress or share via Google Drive.")
    file_obj.name = sanitise_filename(file_obj.name, fallback="material_upload")


def create_material(
    course_id: int,
    title: str,
    description: str,
    material_type: str,
    content_text: str | None,
    external_url: str | None,
    file_attachment: Any,
    section_name: str,
    sort_order: int,
    release_date: datetime | None,
    principal: Any,
) -> CourseMaterial:
    """Creates a new course material in published or scheduled state (CFR-LMS-003)."""
    if not is_course_instructor(course_id, principal):
        raise PermissionDeniedError("Only assigned instructors may upload materials.")

    if file_attachment is not None and material_type == MaterialType.FILE:
        _validate_file_upload(file_attachment)

    try:
        validate_material_payload(
            material_type=material_type,
            content_text=content_text,
            external_url=external_url,
            has_file=file_attachment is not None,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    now = timezone.now()
    status = MaterialFSM.publish(release_date=release_date, now=now)
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0

    with transaction.atomic():
        return CourseMaterial.objects.create(
            course_id=course_id,
            title=title,
            description=description,
            material_type=material_type,
            content_text=content_text or "",
            external_url=external_url or "",
            file_attachment=file_attachment,
            section_name=section_name or "General",
            sort_order=sort_order,
            status=status,
            release_date=release_date,
            uploaded_by=user_id,
        )


def delete_material(material_id: int, principal: Any) -> None:
    """Deletes course material if caller is an instructor for the course."""
    with transaction.atomic():
        material = CourseMaterial.objects.select_for_update().filter(id=material_id).first()
        if not material:
            raise NotFoundError("Course material not found.")
        if not is_course_instructor(material.course_id, principal):
            raise PermissionDeniedError("Only assigned instructors may delete materials.")
        material.delete()
