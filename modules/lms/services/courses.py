"""Database write services for LMS (Course Management).

All state modifications happen through services with atomic transactions.
Raises domain exceptions, never DRF or HTTP exceptions.
"""
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from ..domain import rules, state_machine
from ..domain.entities import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    SubmissionStatus,
)
from ..domain.errors import (
    InvalidAssignmentState,
    LmsDomainError,
    SubmissionOwnershipError,
    UnauthorizedGradingError,
)
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


@transaction.atomic
def create_course_workspace(
    *,
    course_code: str,
    title: str,
    instructor_user_id: int,
    syllabus: str = "",
    schedule: str = "",
) -> CourseWorkspace:
    """Create a new course workspace and enroll the instructor as faculty."""
    course = CourseWorkspace.objects.create(
        course_code=course_code,
        title=title,
        instructor_user_id=instructor_user_id,
        syllabus=syllabus,
        schedule=schedule,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=instructor_user_id,
        role=CourseRole.FACULTY.value,
        can_post_announcements=True,
    )
    return course


@transaction.atomic
def enroll_member(
    *,
    course_id: int,
    user_id: int,
    role: str,
    can_post_announcements: bool = False,
) -> CourseMembership:
    """Enroll or link a user into a course workspace."""
    membership, created = CourseMembership.objects.update_or_create(
        course_id=course_id,
        user_id=user_id,
        defaults={
            "role": role,
            "can_post_announcements": can_post_announcements,
        },
    )
    return membership


@transaction.atomic
def upload_course_material(
    *,
    course_id: int,
    user_id: int,
    user_role: str,
    title: str,
    description: str = "",
    section_or_week: str = "General",
    material_type: str = "file",
    file_url: str = "",
    content: str = "",
    is_scheduled: bool = False,
    scheduled_release_at: datetime | None = None,
) -> CourseMaterial:
    """Upload study materials. TA authoring is prohibited per BR-LMS-004."""
    rules.validate_ta_permission("create_material")
    if user_role not in {CourseRole.FACULTY.value}:
        raise LmsDomainError(f"Role '{user_role}' cannot upload course materials.")

    initial_status = MaterialStatus.SCHEDULED.value if is_scheduled else MaterialStatus.PUBLISHED.value
    published_at = None if is_scheduled else timezone.now()

    return CourseMaterial.objects.create(
        course_id=course_id,
        title=title,
        description=description,
        section_or_week=section_or_week,
        material_type=material_type,
        file_url=file_url,
        content=content,
        status=initial_status,
        scheduled_release_at=scheduled_release_at,
        published_at=published_at,
        uploaded_by_user_id=user_id,
    )


@transaction.atomic
def post_course_announcement(
    *,
    course_id: int,
    user_id: int,
    user_role: str,
    title: str,
    content: str,
    can_post_announcements: bool = False,
) -> CourseAnnouncement:
    """Post course announcement. Faculty, or permitted TAs per BR-LMS-004/007."""
    rules.validate_observer_restriction(user_role, "edit")
    if user_role == CourseRole.TA.value:
        rules.validate_ta_permission("post_announcement", can_post_announcements=can_post_announcements)
    elif user_role != CourseRole.FACULTY.value:
        raise LmsDomainError(f"Role '{user_role}' is not authorized to post course announcements.")

    is_ta = (user_role == CourseRole.TA.value)
    return CourseAnnouncement.objects.create(
        course_id=course_id,
        title=title,
        content=content,
        posted_by_user_id=user_id,
        is_ta_announcement=is_ta,
    )


@transaction.atomic
def create_assignment(
    *,
    course_id: int,
    user_id: int,
    user_role: str,
    title: str,
    instructions: str,
    points_possible: Decimal,
    submission_type: str,
    due_date: datetime,
) -> Assignment:
    """Create course assignment in Draft state (BR-LMS-009, BR-LMS-010)."""
    rules.validate_ta_permission("create_assignment")
    if user_role != CourseRole.FACULTY.value:
        raise LmsDomainError(f"Role '{user_role}' cannot create assignments.")

    rules.validate_assignment_configuration(title, points_possible, submission_type, due_date)

    return Assignment.objects.create(
        course_id=course_id,
        title=title,
        instructions=instructions,
        points_possible=points_possible,
        submission_type=submission_type,
        due_date=due_date,
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=user_id,
    )


@transaction.atomic
def publish_assignment(
    *,
    assignment_id: int,
    user_role: str,
    is_scheduled: bool = False,
    release_date: datetime | None = None,
) -> Assignment:
    """Publish assignment immediately or schedule for future release (CW-LMS-01, BW-LMS-02/03)."""
    rules.validate_ta_permission("edit_assignment")
    if user_role != CourseRole.FACULTY.value:
        raise LmsDomainError("Only Faculty can publish assignments.")

    assignment = Assignment.objects.select_for_update().get(id=assignment_id)
    target_status = AssignmentStatus.SCHEDULED.value if is_scheduled else AssignmentStatus.AVAILABLE.value

    state_machine.validate_assignment_transition(assignment.status, target_status)

    assignment.status = target_status
    assignment.scheduled_release_at = release_date if is_scheduled else None
    if not is_scheduled:
        assignment.published_at = timezone.now()
    assignment.save()
    return assignment


@transaction.atomic
def submit_assignment(
    *,
    assignment_id: int,
    student_user_id: int,
    student_role: str,
    submission_type: str,
    submission_content: str,
) -> StudentSubmission:
    """Submit assignment deliverable with type check and timeliness evaluation (BR-LMS-012/013)."""
    rules.validate_observer_restriction(student_role, "submit")
    if student_role != CourseRole.STUDENT.value:
        raise LmsDomainError("Only enrolled students can submit assignments.")

    assignment = Assignment.objects.get(id=assignment_id)
    now = timezone.now()

    rules.validate_submission_eligibility(
        assignment.status,
        now,
        assignment.scheduled_release_at,
    )
    rules.validate_submission_type(assignment.submission_type, submission_type)

    timeliness = rules.evaluate_submission_timeliness(assignment.due_date, now)

    submission, created = StudentSubmission.objects.update_or_create(
        assignment=assignment,
        student_user_id=student_user_id,
        defaults={
            "submission_type": submission_type,
            "submission_content": submission_content,
            "status": timeliness,
            "submitted_at": now,
        },
    )
    return submission


@transaction.atomic
def grade_submission(
    *,
    submission_id: int,
    grader_user_id: int,
    grader_role: str,
    points: Decimal,
    feedback: str = "",
) -> Grade:
    """Grade submission and record in Draft state (BR-LMS-015, BR-LMS-016)."""
    rules.validate_observer_restriction(grader_role, "grade")
    rules.validate_grading_authority(grader_role)

    submission = StudentSubmission.objects.select_for_update().get(id=submission_id)
    if points < 0 or points > submission.assignment.points_possible:
        raise LmsDomainError(
            f"Points {points} cannot be negative or exceed points possible ({submission.assignment.points_possible})."
        )

    grade, created = Grade.objects.update_or_create(
        submission=submission,
        defaults={
            "points": points,
            "feedback": feedback,
            "status": GradeStatus.DRAFT.value,
            "graded_by_user_id": grader_user_id,
        },
    )
    return grade


@transaction.atomic
def release_assignment_grades(
    *,
    assignment_id: int,
    releaser_user_id: int,
    releaser_role: str,
) -> int:
    """Release all draft grades for an assignment to students (BR-LMS-017, CW-LMS-02)."""
    rules.validate_grade_release_authority(releaser_role)

    now = timezone.now()
    draft_grades = Grade.objects.filter(
        submission__assignment_id=assignment_id,
        status=GradeStatus.DRAFT.value,
    ).select_for_update()

    count = 0
    for grade in draft_grades:
        state_machine.validate_grade_transition(grade.status, GradeStatus.RELEASED.value)
        grade.status = GradeStatus.RELEASED.value
        grade.released_at = now
        grade.released_by_user_id = releaser_user_id
        grade.save()
        count += 1

    return count


@transaction.atomic
def modify_released_grade(
    *,
    grade_id: int,
    modifier_user_id: int,
    modifier_role: str,
    new_points: Decimal,
    reason: str,
) -> Grade:
    """Modify a grade after release and log audit entry (BR-LMS-019)."""
    rules.validate_grade_release_authority(modifier_role)

    grade = Grade.objects.select_for_update().get(id=grade_id)
    if grade.status != GradeStatus.RELEASED.value:
        raise LmsDomainError("Can only perform post-release audit modification on already released grades.")

    if new_points < 0 or new_points > grade.submission.assignment.points_possible:
        raise LmsDomainError(f"Points cannot exceed maximum {grade.submission.assignment.points_possible}.")

    old_points = grade.points
    grade.points = new_points
    grade.save()

    GradeChangeLog.objects.create(
        grade=grade,
        old_points=old_points,
        new_points=new_points,
        reason=reason,
        changed_by_user_id=modifier_user_id,
    )
    return grade
