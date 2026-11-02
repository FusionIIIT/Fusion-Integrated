"""Query selectors for LMS (Course Management).

Read-only queries — no state modifications occur here.
"""
from typing import Sequence

from ..domain import rules
from ..domain.entities import AssignmentStatus, CourseRole, GradeStatus, MaterialStatus
from ..models import (
    Assignment,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    Grade,
    GradeChangeLog,
    StudentSubmission,
)


def get_user_memberships(user_id: int) -> Sequence[CourseMembership]:
    """Return all course memberships for a user."""
    return (
        CourseMembership.objects.filter(user_id=user_id, course__is_active=True)
        .select_related("course")
        .order_by("course__course_code")
    )


def get_membership(course_id: int, user_id: int) -> CourseMembership | None:
    """Return specific course membership for a user if enrolled."""
    return CourseMembership.objects.filter(course_id=course_id, user_id=user_id).first()


def get_course_workspace(course_id: int, user_id: int) -> CourseWorkspace:
    """Return course workspace, validating user course access (BR-LMS-001)."""
    membership = get_membership(course_id, user_id)
    course = CourseWorkspace.objects.filter(id=course_id).first()
    if not course or not membership:
        rules.validate_course_access(is_member=bool(membership), user_id=user_id, course_code=str(course_id))
    return course


def get_course_materials(course_id: int, user_role: str) -> Sequence[CourseMaterial]:
    """Return course materials. Non-faculty can only view published materials (BR-LMS-005)."""
    qs = CourseMaterial.objects.filter(course_id=course_id)
    if user_role != CourseRole.FACULTY.value:
        qs = qs.filter(status=MaterialStatus.PUBLISHED.value)
    return qs.order_by("section_or_week", "-created_at")


def get_course_announcements(course_id: int) -> Sequence[CourseAnnouncement]:
    """Return timestamped course announcements visible to all members (BR-LMS-008)."""
    return CourseAnnouncement.objects.filter(course_id=course_id).order_by("-posted_at")


def get_course_assignments(course_id: int, user_role: str) -> Sequence[Assignment]:
    """Return course assignments. Non-faculty only view available assignments (BR-LMS-010)."""
    qs = Assignment.objects.filter(course_id=course_id)
    if user_role in {CourseRole.STUDENT.value, CourseRole.OBSERVER.value}:
        qs = qs.filter(status=AssignmentStatus.AVAILABLE.value)
    return qs.order_by("due_date")


def get_assignment_submissions(
    assignment_id: int,
    user_id: int,
    user_role: str,
) -> Sequence[StudentSubmission]:
    """Return submissions. Students only see their own (BR-LMS-014); Observers cannot view (BR-LMS-003)."""
    rules.validate_observer_restriction(user_role, "view_submission")

    qs = StudentSubmission.objects.filter(assignment_id=assignment_id).select_related("grade")
    if user_role == CourseRole.STUDENT.value:
        qs = qs.filter(student_user_id=user_id)
    return qs.order_by("-submitted_at")


def get_submission_detail(submission_id: int, user_id: int, user_role: str) -> StudentSubmission | None:
    """Return specific submission validating ownership and observer restrictions."""
    rules.validate_observer_restriction(user_role, "view_submission")
    submission = StudentSubmission.objects.filter(id=submission_id).select_related("assignment", "grade").first()
    if submission and user_role == CourseRole.STUDENT.value:
        rules.validate_submission_ownership(submission.student_user_id, user_id, user_role)
    return submission


def get_student_course_grades(course_id: int, student_user_id: int) -> Sequence[Grade]:
    """Return released grades for a student in a course (BR-LMS-016, BR-LMS-018)."""
    return (
        Grade.objects.filter(
            submission__assignment__course_id=course_id,
            submission__student_user_id=student_user_id,
            status=GradeStatus.RELEASED.value,
        )
        .select_related("submission", "submission__assignment")
        .order_by("submission__assignment__due_date")
    )


def get_grade_change_logs(grade_id: int) -> Sequence[GradeChangeLog]:
    """Return audit history of post-release grade modifications (BR-LMS-019)."""
    return GradeChangeLog.objects.filter(grade_id=grade_id).order_by("-changed_at")
