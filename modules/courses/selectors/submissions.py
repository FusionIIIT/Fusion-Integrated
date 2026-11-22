"""Selectors for Course Submissions with role and privacy scoping (BR-LMS-001, BR-LMS-003, BR-LMS-004, BR-LMS-014)."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.courses.models import (
    CourseAssignment,
    CourseSubmission,
    CourseWorkspace,
)
from modules.courses.selectors import scoping


def visible_submissions(
    workspace: CourseWorkspace,
    assignment: CourseAssignment,
    principal,
) -> QuerySet[CourseSubmission]:
    """Returns submissions for an assignment visible to the requesting actor.

    Faculty instructors and assigned TAs see ALL student submissions for the course (BR-LMS-004).

    Enrolled students see ONLY their own submission (BR-LMS-014).

    Observers are NOT permitted to view student submissions (BR-LMS-003).
    """
    if not principal:
        return CourseSubmission.objects.none()

    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership:
        return CourseSubmission.objects.none()

    if membership.role == "observer":
        return CourseSubmission.objects.none()

    qs = CourseSubmission.objects.filter(
        workspace=workspace,
        assignment=assignment,
    )

    if scoping.is_course_instructor(workspace, principal) or membership.role == "ta":
        return qs.order_by("-submitted_at", "-id")

    if membership.role == "student":
        return qs.filter(student_id=principal.user_id).order_by("-submitted_at", "-id")

    return CourseSubmission.objects.none()


def get_student_submission(
    workspace: CourseWorkspace,
    assignment: CourseAssignment,
    principal,
) -> CourseSubmission | None:
    """Returns the caller's own submission for the assignment if enrolled as a student."""
    if not principal:
        return None

    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership or membership.role != "student":
        return None

    return CourseSubmission.objects.filter(
        workspace=workspace,
        assignment=assignment,
        student_id=principal.user_id,
    ).first()


def get_submission_for_actor(
    workspace_id: int,
    assignment_id: int,
    submission_id: int,
    principal,
) -> CourseSubmission | None:
    """Retrieves a single submission scoped strictly to the specified workspace and assignment."""
    workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return None

    assignment = CourseAssignment.objects.filter(
        id=assignment_id,
        workspace=workspace,
    ).first()
    if not assignment:
        return None

    return (
        visible_submissions(workspace, assignment, principal)
        .filter(id=submission_id)
        .first()
    )
