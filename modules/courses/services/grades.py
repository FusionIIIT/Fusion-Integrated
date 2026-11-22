"""Course Grades and Evaluation domain services (CFR-LMS-010, CFR-LMS-011, BR-LMS-015, BR-LMS-016, BR-LMS-017, BR-LMS-019)."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from django.db import transaction
from django.utils import timezone

from modules.courses.domain.grades import (
    GradeInputDTO,
    GradeReleaseDTO,
    GradeValidationError,
    validate_grade_score,
    validate_grader_authority,
    validate_release_authority,
)
from modules.courses.models import (
    CourseAssignment,
    CourseGrade,
    CourseGradeAudit,
    CourseSubmission,
    CourseWorkspace,
)


def record_or_update_grade(
    workspace: CourseWorkspace,
    submission_id: int,
    grader_id: int,
    grader_role: str,
    score: Decimal,
    feedback: str = "",
) -> CourseGrade:
    """Record or update evaluation and marks for a student submission (UC-LMS-012, BR-LMS-015).

    - Only Faculty ('instructor') and TAs ('ta') can grade.
    - Validates marks against assignment maximum points.
    - Attributed to the grader (BR-LMS-015).
    - If modifying an already-released grade, records post-release audit log (BR-LMS-019).
    """
    validate_grader_authority(grader_role)

    try:
        submission = CourseSubmission.objects.select_related("assignment", "workspace").get(
            id=submission_id,
            workspace=workspace,
        )
    except CourseSubmission.DoesNotExist:
        raise GradeValidationError("Student submission not found in this course workspace.")

    assignment = submission.assignment
    max_pts = assignment.max_points if assignment.max_points is not None else Decimal("100.00")
    validate_grade_score(score, max_pts)

    cleaned_feedback = feedback.strip() if feedback else ""

    with transaction.atomic():
        grade, created = CourseGrade.objects.select_for_update().get_or_create(
            submission=submission,
            defaults={
                "workspace": workspace,
                "assignment": assignment,
                "student_id": submission.student_id,
                "grader_id": grader_id,
                "score": score,
                "feedback": cleaned_feedback,
                "status": "draft",
                "graded_at": timezone.now(),
            },
        )

        if created:
            # Audit initial grading action
            CourseGradeAudit.objects.create(
                workspace=workspace,
                grade=grade,
                actor_id=grader_id,
                action="graded",
                score_before=None,
                score_after=score,
                feedback_before="",
                feedback_after=cleaned_feedback,
                status_before="",
                status_after="draft",
            )
        else:
            prev_score = grade.score
            prev_feedback = grade.feedback
            prev_status = grade.status

            score_changed = prev_score != score
            feedback_changed = prev_feedback != cleaned_feedback

            if score_changed or feedback_changed:
                grade.score = score
                grade.feedback = cleaned_feedback
                grade.grader_id = grader_id  # update grader attribution
                grade.graded_at = timezone.now()
                grade.save(update_fields=["score", "feedback", "grader_id", "graded_at", "updated_at"])

                # Audit: if released, log post-release modification (BR-LMS-019); otherwise log draft update
                action_name = "updated_post_release" if prev_status == "released" else "updated"
                CourseGradeAudit.objects.create(
                    workspace=workspace,
                    grade=grade,
                    actor_id=grader_id,
                    action=action_name,
                    score_before=prev_score,
                    score_after=score,
                    feedback_before=prev_feedback,
                    feedback_after=cleaned_feedback,
                    status_before=prev_status,
                    status_after=prev_status,
                )

    return grade


def release_assignment_grades(
    workspace: CourseWorkspace,
    assignment_id: int,
    actor_id: int,
    actor_role: str,
    submission_id: Optional[int] = None,
) -> List[CourseGrade]:
    """Release draft grades to students for an assignment (UC-LMS-013, BR-LMS-017).

    - Only Faculty ('instructor') can release grades.
    - Transitions matching grades from Draft to Released.
    - Logs release audit trail (BR-LMS-019).
    """
    validate_release_authority(actor_role)

    try:
        assignment = CourseAssignment.objects.get(id=assignment_id, workspace=workspace)
    except CourseAssignment.DoesNotExist:
        raise GradeValidationError("Assignment not found in this course workspace.")

    with transaction.atomic():
        query = CourseGrade.objects.select_for_update().filter(
            workspace=workspace,
            assignment=assignment,
            status="draft",
        )
        if submission_id is not None:
            query = query.filter(submission_id=submission_id)

        draft_grades = list(query)
        now = timezone.now()
        released_grades = []

        for grade in draft_grades:
            prev_status = grade.status
            grade.status = "released"
            grade.released_at = now
            grade.released_by_id = actor_id
            grade.save(update_fields=["status", "released_at", "released_by_id", "updated_at"])

            CourseGradeAudit.objects.create(
                workspace=workspace,
                grade=grade,
                actor_id=actor_id,
                action="released",
                score_before=grade.score,
                score_after=grade.score,
                feedback_before=grade.feedback,
                feedback_after=grade.feedback,
                status_before=prev_status,
                status_after="released",
            )
            released_grades.append(grade)

    return released_grades
