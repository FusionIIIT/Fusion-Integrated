"""Course Grades selectors (CFR-LMS-010, CFR-LMS-011, BR-LMS-003, BR-LMS-016, BR-LMS-018)."""
from __future__ import annotations

from typing import List, Optional
from django.db.models import QuerySet

from modules.courses.models import (
    CourseGrade,
    CourseGradeAudit,
    CourseSubmission,
    CourseWorkspace,
)


def get_grade_for_submission(
    workspace: CourseWorkspace,
    submission_id: int,
    actor_role: str,
    actor_id: int,
) -> Optional[CourseGrade]:
    """Retrieve grade for a submission respecting role-based visibility (BR-LMS-003, BR-LMS-016, BR-LMS-018).

    - Observers ('observer'): Always None.
    - Faculty ('instructor') & TAs ('ta'): Grade returned if it exists.
    - Students ('student'): Grade returned ONLY if owned and released.
    """
    if actor_role == "observer":
        return None

    try:
        submission = CourseSubmission.objects.get(id=submission_id, workspace=workspace)
    except CourseSubmission.DoesNotExist:
        return None

    try:
        grade = CourseGrade.objects.select_related("assignment", "submission", "workspace").get(
            submission=submission,
            workspace=workspace,
        )
    except CourseGrade.DoesNotExist:
        return None

    if actor_role in ("instructor", "ta"):
        return grade

    if actor_role == "student":
        if submission.student_id == actor_id and grade.status == "released":
            return grade
        return None

    return None


def list_grades_for_assignment(
    workspace: CourseWorkspace,
    assignment_id: int,
    actor_role: str,
) -> QuerySet[CourseGrade]:
    """List all grades for an assignment in a workspace (Faculty and TA only)."""
    if actor_role not in ("instructor", "ta"):
        return CourseGrade.objects.none()

    return CourseGrade.objects.filter(
        workspace=workspace,
        assignment_id=assignment_id,
    ).select_related("submission", "assignment")


def list_student_released_grades(
    workspace: CourseWorkspace,
    student_id: int,
) -> QuerySet[CourseGrade]:
    """List all released grades for a specific student in a workspace (BR-LMS-018)."""
    return CourseGrade.objects.filter(
        workspace=workspace,
        student_id=student_id,
        status="released",
    ).select_related("assignment", "submission")


def get_grade_audit_logs(
    workspace: CourseWorkspace,
    grade_id: int,
    actor_role: str,
) -> QuerySet[CourseGradeAudit]:
    """Retrieve audit history for a grade (BR-LMS-019). Authorized for Faculty and TA only."""
    if actor_role not in ("instructor", "ta"):
        return CourseGradeAudit.objects.none()

    return CourseGradeAudit.objects.filter(
        workspace=workspace,
        grade_id=grade_id,
    ).order_by("-created_at")
