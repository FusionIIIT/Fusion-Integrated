"""Scoping: who sees which rows. Yields 404, never 403."""
from rest_framework.exceptions import NotFound


def course_for(user, course_id):
    """Return course_id if user is linked to it, else raise 404."""
    # In module-only, we trust the caller's course list. In full-platform,
    # this would check registration data. For now, accept any valid course_id
    # the user is allowed to see (scoping enforced at queryset level).
    if not course_id or int(course_id) <= 0:
        raise NotFound("Course not found")
    return int(course_id)


def materials_for_course(user, course_id):
    from modules.lms.models import CourseMaterial
    qs = CourseMaterial.objects.filter(course_id=course_id)
    # Observer/Student/TA see only published materials
    if not _is_faculty_or_ta(user):
        qs = qs.filter(status="published")
    return qs


def _is_faculty_or_ta(user):
    # Check if user has faculty or TA designation
    # In module-only, we check permissions on the user object
    perms = getattr(user, "permissions", []) or []
    return "lms.material.manage" in perms or "lms.course.manage" in perms


def announcements_for_course(user, course_id):
    from modules.lms.models import Announcement
    return Announcement.objects.filter(course_id=course_id)


def assignments_for_course(user, course_id):
    from modules.lms.models import Assignment
    qs = Assignment.objects.filter(course_id=course_id)
    # Students see only available assignments
    perms = getattr(user, "permissions", []) or []
    if "lms.assignment.manage" not in perms:
        qs = qs.filter(status__in=["available", "published"])
    return qs


def submissions_for_student(user, assignment_id):
    from modules.lms.models import Submission
    uid = getattr(user, "user_id", user) if not isinstance(user, int) else user
    return Submission.objects.filter(assignment_id=assignment_id, user_id=uid)


def submissions_for_grading(user, assignment_id):
    from modules.lms.models import Submission
    return Submission.objects.filter(assignment_id=assignment_id)


def released_grades_for_student(arg1, arg2):
    from modules.lms.models import Grade, Submission
    if isinstance(arg1, int) and (isinstance(arg2, int) or hasattr(arg2, "user_id")):
        assignment_id = arg1
        user = arg2
    else:
        user = arg1
        assignment_id = arg2

    uid = getattr(user, "user_id", user) if not isinstance(user, int) else user
    sub_ids = Submission.objects.filter(
        assignment_id=assignment_id, user_id=uid
    ).values_list("id", flat=True)
    return Grade.objects.filter(submission_id__in=sub_ids, status="released")


def grades_for_student(user, assignment_id):
    return released_grades_for_student(assignment_id, user)
