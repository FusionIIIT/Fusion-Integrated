from django.db.models import Q, QuerySet
from django.utils import timezone
from modules.lms.domain.constants import ContentStatus
from modules.lms.models import Announcement, CourseMaterial, ModuleSection


def get_sections_for_course(course_id: int) -> QuerySet:
    """Returns sections ordered by display order."""
    return ModuleSection.objects.filter(
        course_id=course_id
    ).order_by("order")


def get_materials_for_section(section_id: int, is_staff: bool = False) -> QuerySet:
    """Returns materials for section. Non-staff only see published, unembargoed materials."""
    qs = CourseMaterial.objects.filter(section_id=section_id)
    if not is_staff:
        now = timezone.now()
        qs = qs.filter(status=ContentStatus.PUBLISHED).filter(
            Q(release_date__isnull=True) | Q(release_date__lte=now)
        )
    return qs


def get_announcements_for_course(course_id: int) -> QuerySet:
    """Returns announcements ordered by creation date."""
    return Announcement.objects.filter(
        course_id=course_id
    ).order_by("-created_at")
