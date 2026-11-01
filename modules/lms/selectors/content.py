from django.db.models import Q, QuerySet
from django.utils import timezone

from modules.lms.models import (
    Assignment,
    CourseAnnouncement,
    CourseMaterial,
    CourseSection,
    SubmissionGrade,
)


def sections(course_id: int) -> QuerySet[CourseSection]:
    return CourseSection.objects.filter(course_id=course_id).order_by("sort_order", "id")


def materials(course_id: int, *, can_manage: bool) -> QuerySet[CourseMaterial]:
    qs = CourseMaterial.objects.filter(course_id=course_id).select_related("section")
    if not can_manage:
        qs = qs.filter(status="published").filter(
            Q(release_at__isnull=True) | Q(release_at__lte=timezone.now()))
    return qs.order_by("section__sort_order", "created_at")


def announcements(course_id: int) -> QuerySet[CourseAnnouncement]:
    return CourseAnnouncement.objects.filter(course_id=course_id).order_by(
        "-published_at", "-id")


def assignments(course_id: int, *, can_manage: bool) -> QuerySet[Assignment]:
    qs = Assignment.objects.filter(course_id=course_id)
    if not can_manage:
        now = timezone.now()
        qs = qs.filter(status="available").filter(
            Q(release_at__isnull=True) | Q(release_at__lte=now))
    return qs.order_by("due_at", "id")


def grades_for_student(user_id: int):
    return SubmissionGrade.objects.filter(
        submission__user_id=user_id, status="released").select_related(
            "submission", "submission__assignment", "submission__assignment__course")
