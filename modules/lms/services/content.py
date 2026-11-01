from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.lms.domain.states import (
    ASSIGNMENT_AVAILABLE,
    GRADE_DRAFT,
    GRADE_RELEASED,
    MATERIAL_PUBLISHED,
    assignment_state,
    material_state,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseSection,
    ReleasedGradeChange,
    SubmissionGrade,
)
from modules.lms.services.access import allow_ta, require_role


def update_course(*, course, ref, syllabus: str, schedule: str) -> None:
    require_role(ref, "faculty")
    course.syllabus, course.schedule = syllabus, schedule
    course.save(update_fields=["syllabus", "schedule", "updated_at"])


def create_section(*, course, ref, **data) -> CourseSection:
    require_role(ref, "faculty")
    return CourseSection.objects.create(course=course, **data)


def save_material(*, course, ref, actor, data, material_id=None) -> CourseMaterial:
    require_role(ref, "faculty")
    section = data.get("section")
    if section and section.course_id != course.id:
        raise NotFoundError("No such course section.")
    now = timezone.now()
    if material_id:
        material = CourseMaterial.objects.filter(pk=material_id, course=course).first()
        if not material:
            raise NotFoundError("No such course material.")
        if material.status == MATERIAL_PUBLISHED:
            # Editing published content is supported by the Manage Materials UC.
            for key, value in data.items():
                setattr(material, key, value)
            material.status = material_state(release_at=material.release_at, now=now)
            material.published_at = now if material.status == MATERIAL_PUBLISHED else None
            material.save()
            return material
        for key, value in data.items():
            setattr(material, key, value)
        material.status = material_state(release_at=material.release_at, now=now)
        material.published_at = now if material.status == MATERIAL_PUBLISHED else None
        material.save()
        return material
    state = material_state(release_at=data.get("release_at"), now=now)
    return CourseMaterial.objects.create(
        course=course, created_by_user_id=actor.user_id,
        status=state, published_at=now if state == MATERIAL_PUBLISHED else None,
        **data)


def post_announcement(*, course, ref, actor, title: str, content: str):
    if ref.role == "teaching_assistant":
        allow_ta(ref, "announce")
    else:
        require_role(ref, "faculty")
    now = timezone.now()
    return CourseAnnouncement.objects.create(
        course=course, title=title, content=content,
        posted_by_user_id=actor.user_id, published_at=now)


def save_assignment(*, course, ref, actor, data, assignment_id=None):
    require_role(ref, "faculty")
    if assignment_id:
        assignment = Assignment.objects.filter(
            pk=assignment_id, course=course, status="draft").first()
        if not assignment:
            raise NotFoundError("No editable draft assignment was found.")
        for key, value in data.items():
            setattr(assignment, key, value)
        assignment.save()
        return assignment
    return Assignment.objects.create(
        course=course, created_by_user_id=actor.user_id, status="draft", **data)


def publish_assignment(*, course, ref, assignment_id: int):
    require_role(ref, "faculty")
    with transaction.atomic():
        assignment = Assignment.objects.select_for_update().filter(
            pk=assignment_id, course=course).first()
        if not assignment:
            raise NotFoundError("No such assignment.")
        if assignment.status != "draft":
            raise ConflictError("Only a draft assignment may be published.")
        now = timezone.now()
        assignment.status = assignment_state(release_at=assignment.release_at, now=now)
        assignment.published_at = now
        assignment.save(update_fields=["status", "published_at", "updated_at"])
        return assignment


def submit(*, assignment, ref, actor, content_type: str, text: str = "",
           link: str = "", file=None):
    require_role(ref, "student")
    if assignment.status != ASSIGNMENT_AVAILABLE or (
            assignment.release_at and assignment.release_at > timezone.now()):
        raise ConflictError("This assignment is not available for submission.")
    now = timezone.now()
    if now >= assignment.due_at:
        raise ConflictError(
            "Late-submission policy is unresolved; only on-time submissions are accepted.",
            code="late_submission_policy_unresolved")
    if content_type != assignment.submission_type:
        raise ConflictError("Submission type must match the assignment configuration.",
                            code="submission_type_mismatch")
    with transaction.atomic():
        locked = Assignment.objects.select_for_update().get(pk=assignment.pk)
        if AssignmentSubmission.objects.filter(
                assignment=locked, user_id=actor.user_id).exists():
            raise ConflictError(
                "Resubmission policy is unresolved; a second submission cannot be recorded.",
                code="resubmission_policy_unresolved")
        return AssignmentSubmission.objects.create(
            assignment=locked, user_id=actor.user_id,
            content_type=content_type, text=text, link=link, file=file,
            submitted_at=now)


def grade_submission(*, submission, ref, actor, points, feedback):
    if ref.role == "teaching_assistant":
        allow_ta(ref, "grade")
    else:
        require_role(ref, "faculty")
    if points < 0 or points > submission.assignment.points_possible:
        raise ConflictError("Points must be within the assignment's points possible.",
                            code="points_out_of_range")
    now = timezone.now()
    with transaction.atomic():
        grade = (SubmissionGrade.objects.select_for_update()
                 .filter(submission=submission).first())
        if grade is None:
            return SubmissionGrade.objects.create(
                submission=submission, points=points, feedback=feedback,
                status=GRADE_DRAFT, graded_by_user_id=actor.user_id, graded_at=now)
        if (grade.status == GRADE_RELEASED and
                (grade.points != points or grade.feedback != feedback)):
            ReleasedGradeChange.objects.create(
                grade=grade, old_points=grade.points, new_points=points,
                old_feedback=grade.feedback, new_feedback=feedback,
                changed_by_user_id=actor.user_id)
        grade.points, grade.feedback = points, feedback
        grade.graded_by_user_id, grade.graded_at = actor.user_id, now
        grade.save(update_fields=["points", "feedback", "graded_by_user_id",
                                  "graded_at", "updated_at"])
        return grade


def release_grades(*, course, ref, actor, grade_ids: list[int]):
    require_role(ref, "faculty")
    if not grade_ids:
        raise ConflictError("Select at least one draft grade to release.")
    now = timezone.now()
    with transaction.atomic():
        grades = list(SubmissionGrade.objects.select_for_update().filter(
            pk__in=grade_ids, submission__assignment__course=course,
            status=GRADE_DRAFT))
        if len(grades) != len(set(grade_ids)):
            raise NotFoundError("One or more draft grades were not found.")
        for grade in grades:
            grade.status = GRADE_RELEASED
            grade.released_by_user_id = actor.user_id
            grade.released_at = now
        SubmissionGrade.objects.bulk_update(
            grades, ["status", "released_by_user_id", "released_at", "updated_at"])
        return grades
