from django.db.models import Q, QuerySet
from django.utils import timezone
from modules.lms.domain.constants import ContentStatus
from modules.lms.models import Assignment


def get_assignments_for_course(course_id: int, is_staff: bool = False) -> QuerySet:
    """Returns assignments for the course. Non-staff only see published, unembargoed assignments."""
    qs = Assignment.objects.filter(course_id=course_id)
    if not is_staff:
        now = timezone.now()
        qs = qs.filter(status=ContentStatus.PUBLISHED).filter(
            Q(release_date__isnull=True) | Q(release_date__lte=now)
        )
    return qs.order_by("-due_date", "-created_at")


def get_assignment_by_id(assignment_id: int) -> Assignment | None:
    """Returns the assignment with the given ID or None."""
    return Assignment.objects.filter(id=assignment_id).first()
