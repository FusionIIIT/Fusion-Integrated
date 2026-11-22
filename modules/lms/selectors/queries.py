"""Read queries for the LMS module."""
from modules.lms.models import (
    Announcement,
    Assignment,
    CourseMaterial,
    Grade,
    Submission,
)


def materials_for_course(course_id, published_only=False):
    qs = CourseMaterial.objects.filter(course_id=course_id)
    if published_only:
        qs = qs.filter(status="published")
    return qs


def announcements_for_course(course_id):
    return Announcement.objects.filter(course_id=course_id)


def assignments_for_course(course_id, published_only=False):
    qs = Assignment.objects.filter(course_id=course_id)
    if published_only:
        qs = qs.filter(status__in=["available", "published"])
    return qs


def submissions_for_assignment(assignment_id, student_id=None):
    qs = Submission.objects.filter(assignment_id=assignment_id)
    if student_id is not None:
        qs = qs.filter(user_id=student_id)
    return qs


def grades_for_submission(submission_id):
    return Grade.objects.filter(submission_id=submission_id)


def released_grades_for_student(assignment_id, student_id):
    sub_ids = Submission.objects.filter(
        assignment_id=assignment_id, user_id=student_id
    ).values_list("id", flat=True)
    return Grade.objects.filter(submission_id__in=sub_ids, status="released")
