from django.core.exceptions import PermissionDenied
from modules.lms.domain.constants import ContentStatus, MaterialKind, Role
from modules.lms.models import Announcement, CourseMaterial, ModuleSection


def create_section(course_id: int, title: str, order: int = 0, is_published: bool = False) -> ModuleSection:
    return ModuleSection.objects.create(
        course_id=course_id,
        title=title,
        order=order,
        is_published=is_published,
    )


def update_section(section_id: int, **fields) -> ModuleSection:
    section = ModuleSection.objects.get(id=section_id)
    for key, value in fields.items():
        setattr(section, key, value)
    section.save()
    return section


def create_material(
    section_id: int,
    title: str,
    kind: str = MaterialKind.FILE,
    content_text: str = "",
    file_storage_key: str = "",
    link_url: str = "",
    status: str = ContentStatus.DRAFT,
    release_date=None,
) -> CourseMaterial:
    return CourseMaterial.objects.create(
        section_id=section_id,
        title=title,
        kind=kind,
        content_text=content_text,
        file_storage_key=file_storage_key,
        link_url=link_url,
        status=status,
        release_date=release_date,
    )


def create_announcement(
    course_id: int,
    author_user_id: int,
    title: str,
    content: str,
    author_role: str = Role.INSTRUCTOR,
) -> Announcement:
    if author_role != Role.INSTRUCTOR:
        raise PermissionDenied(
            "TA announcement creation is pending policy clarification (ISS-LMS-002). Only instructors can publish announcements."
        )
    return Announcement.objects.create(
        course_id=course_id,
        author_user_id=author_user_id,
        author_role=author_role,
        title=title,
        content=content,
    )
