"""Ownership- and membership-scoped LMS student submission reads."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.directory import contracts as directory
from modules.lms.domain.entities import CourseRole, SubmissionStatus
from modules.lms.models import (
    CourseAssignment,
    CourseMembership,
    CourseSubmission,
)
from modules.lms.selectors.deadlines import calculate_deadline_info


def _submission_to_dict(s: CourseSubmission) -> dict[str, Any]:
    return {
        "id": s.id,
        "assignment_id": s.assignment_id,
        "student_user_id": s.student_user_id,
        "submission_type": s.submission_type,
        "status": s.status,
        "submitted_at": s.submitted_at.isoformat(),
        "file_name": s.file_name,
        "file_size": s.file_size,
        "has_file": bool(s.file),
        "content_text": s.content_text,
        "link_url": s.link_url,
        "attempt_number": s.attempt_number,
        "is_latest": s.is_latest,
        "created_at": s.created_at.isoformat(),
    }


def get_student_submission_history(
    *,
    principal,
    course_code: str,
    assignment_id: int,
    student_user_id: int | None = None,
) -> dict[str, Any] | None:
    """Retrieve own submission history and status for a student (CFR-LMS-009, BR-LMS-014).

    Faculty and TAs may also view a specific student's submission history.
    Students may view ONLY their own submission data (AFR-LMS-009.1, BR-LMS-014).
    Observers are strictly denied access to individual student submissions (AFR-LMS-015.2).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    # Observers cannot view student submissions (AFR-LMS-015.2)
    if membership.role == CourseRole.OBSERVER:
        return None

    # Determine target student user id
    if membership.role == CourseRole.STUDENT:
        # Students can view only their own submission data (BR-LMS-014)
        if student_user_id is not None and student_user_id != principal.user_id:
            raise PermissionDeniedError("You can only view your own assignment submissions.")
        target_student_id = principal.user_id
    else:
        # Faculty or TA viewing a student's history
        target_student_id = student_user_id if student_user_id is not None else principal.user_id

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        return None

    # Non-faculty cannot view unreleased/draft assignments
    now = timezone.now()
    if membership.role != CourseRole.FACULTY:
        if assignment.status == "draft":
            return None
        if assignment.status == "scheduled" and (
            not assignment.release_at or assignment.release_at > now
        ):
            return None

    submissions = list(
        CourseSubmission.objects.filter(
            assignment=assignment,
            student_user_id=target_student_id,
        ).order_by("-submitted_at")
    )

    latest = next((s for s in submissions if s.is_latest), None) or (
        submissions[0] if submissions else None
    )

    # Determine overall status (submitted, late, missing, not_submitted)
    dl_info = calculate_deadline_info(assignment, student_user_id=target_student_id)
    if latest:
        effective_status = latest.status
    elif dl_info["effective_due_at"] and now > assignment.due_at:
        # Check if past effective due date
        effective_due = (
            assignment.extensions.filter(user_id=target_student_id)
            .values_list("extended_due_at", flat=True)
            .first()
            or assignment.due_at
        )
        effective_status = (
            SubmissionStatus.MISSING if now > effective_due else "not_submitted"
        )
    else:
        effective_status = "not_submitted"

    return {
        "assignment_id": assignment.id,
        "course_code": membership.course.code,
        "student_user_id": target_student_id,
        "status": effective_status,
        "has_submitted": latest is not None,
        "latest_submission": _submission_to_dict(latest) if latest else None,
        "history": [_submission_to_dict(s) for s in submissions],
        "total_attempts": len(submissions),
        "deadline_info": dl_info,
    }


def list_assignment_submissions(
    *,
    principal,
    course_code: str,
    assignment_id: int,
) -> dict[str, Any] | None:
    """List all latest submissions for an assignment (Faculty and TAs only, AFR-LMS-014.2).

    Students and Observers cannot access class submissions (AFR-LMS-015.2, BR-LMS-014).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    if membership.role not in {CourseRole.FACULTY, CourseRole.TA}:
        return None

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        return None

    latest_submissions = list(
        CourseSubmission.objects.filter(assignment=assignment, is_latest=True)
        .select_related("grade")
        .order_by("-submitted_at")
    )

    # Resolve student and grader facts via directory contract lookup
    student_user_ids = {s.student_user_id for s in latest_submissions}
    grader_user_ids = {
        s.grade.graded_by_user_id
        for s in latest_submissions
        if hasattr(s, "grade") and s.grade
    }
    all_user_ids = list(student_user_ids | grader_user_ids)
    user_facts = directory.get_users(all_user_ids) if all_user_ids else {}

    items = []
    on_time_count = 0
    late_count = 0

    for s in latest_submissions:
        user_info = user_facts.get(s.student_user_id)
        if s.status == SubmissionStatus.SUBMITTED:
            on_time_count += 1
        elif s.status == SubmissionStatus.LATE:
            late_count += 1

        grade_obj = getattr(s, "grade", None)
        grade_dict = None
        if grade_obj:
            grader_info = user_facts.get(grade_obj.graded_by_user_id)
            g_name = (
                grader_info.display_name
                if grader_info
                else f"User {grade_obj.graded_by_user_id}"
            )
            grade_dict = {
                "id": grade_obj.id,
                "submission_id": grade_obj.submission_id,
                "assignment_id": grade_obj.assignment_id,
                "student_user_id": grade_obj.student_user_id,
                "score": str(grade_obj.score),
                "points_possible": str(assignment.points_possible),
                "status": grade_obj.status,
                "graded_by_user_id": grade_obj.graded_by_user_id,
                "graded_by_name": g_name,
                "graded_by_email": grader_info.email if grader_info else "",
                "graded_at": grade_obj.graded_at.isoformat() if grade_obj.graded_at else "",
            }

        items.append({
            "id": s.id,
            "assignment_id": s.assignment_id,
            "student_user_id": s.student_user_id,
            "student_name": user_info.display_name if user_info else f"User {s.student_user_id}",
            "student_email": user_info.email if user_info else "",
            "submission_type": s.submission_type,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat(),
            "file_name": s.file_name,
            "file_size": s.file_size,
            "has_file": bool(s.file),
            "content_text": s.content_text,
            "link_url": s.link_url,
            "attempt_number": s.attempt_number,
            "is_latest": s.is_latest,
            "created_at": s.created_at.isoformat(),
            "grade": grade_dict,
        })

    return {
        "assignment_id": assignment.id,
        "course_code": membership.course.code,
        "assignment_title": assignment.title,
        "submission_type": assignment.submission_type,
        "total_submissions": len(items),
        "on_time_count": on_time_count,
        "late_count": late_count,
        "submissions": items,
    }


def get_submission_for_download(
    *,
    principal,
    course_code: str,
    assignment_id: int,
    submission_id: int,
) -> CourseSubmission | None:
    """Retrieve submission file for download with strict authorization checks.

    - Faculty & TAs can download any submission in their assigned course.
    - Students can download ONLY their own submission attachment.
    - Observers and unlinked users are denied access (AFR-LMS-015.2).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    if membership.role == CourseRole.OBSERVER:
        return None

    submission = (
        CourseSubmission.objects.filter(
            id=submission_id,
            assignment_id=assignment_id,
            assignment__course=membership.course,
        )
        .select_related("assignment", "assignment__course")
        .first()
    )
    if submission is None or not submission.file:
        return None

    # Student privacy: student can download only their own submission file
    if membership.role == CourseRole.STUDENT and submission.student_user_id != principal.user_id:
        return None

    return submission
