"""Write services for the LMS module."""
from django.db import transaction

from modules.lms.domain.state_machine import (
    ASSIGNMENT_TRANSITIONS,
    GRADE_TRANSITIONS,
    MATERIAL_TRANSITIONS,
    transition,
)
from modules.lms.models import (
    Announcement,
    Assignment,
    CourseMaterial,
    Grade,
    GradeAudit,
    Submission,
)


# --- Materials ---
def create_material(*, course_id, user_id, title, material_type, content="",
                   section="", status="draft", release_at=None):
    return CourseMaterial.objects.create(
        course_id=course_id, user_id=user_id, title=title,
        material_type=material_type, content=content, section=section,
        status=status, release_at=release_at,
    )


def publish_material(material_id):
    m = CourseMaterial.objects.get(pk=material_id)
    new = transition(MATERIAL_TRANSITIONS, m.status, "publish")
    if new is None:
        raise ValueError("Cannot publish from current state")
    m.status = new
    m.save(update_fields=["status", "updated_at"])
    return m


def schedule_material(material_id, release_at):
    m = CourseMaterial.objects.get(pk=material_id)
    new = transition(MATERIAL_TRANSITIONS, m.status, "schedule")
    if new is None:
        raise ValueError("Cannot schedule from current state")
    m.status = new
    m.release_at = release_at
    m.save(update_fields=["status", "release_at", "updated_at"])
    return m


# --- Announcements ---
def create_announcement(*, course_id, author_id, content, is_pinned=False):
    return Announcement.objects.create(
        course_id=course_id, user_id=author_id, content=content, is_pinned=is_pinned,
    )


# --- Assignments ---
def create_assignment(*, course_id, user_id, title, instructions="", due_at,
                     submission_type="file", points_possible=0, max_attempts=1):
    return Assignment.objects.create(
        course_id=course_id, user_id=user_id, title=title, instructions=instructions,
        due_at=due_at, submission_type=submission_type, points_possible=points_possible,
        max_attempts=max_attempts,
    )


def publish_assignment(assignment_id, release_at=None):
    a = Assignment.objects.get(pk=assignment_id)
    event = "publish_scheduled" if release_at else "publish_immediate"
    new = transition(ASSIGNMENT_TRANSITIONS, a.status, event)
    if new is None:
        raise ValueError("Cannot publish from current state")
    a.status = new
    if release_at:
        a.release_at = release_at
    a.save(update_fields=["status", "release_at", "updated_at"])
    return a


# --- Submissions ---
@transaction.atomic
def submit_assignment(*, assignment_id, student_id, submission_type, content="",
                     file=None, is_late=False):
    assignment = Assignment.objects.get(pk=assignment_id)
    status_val = "late" if is_late else "submitted"
    return Submission.objects.create(
        assignment=assignment, user_id=student_id, submission_type=submission_type,
        content=content, file=file, status=status_val, is_late=is_late,
    )


# --- Grading ---
@transaction.atomic
def grade_submission(*, submission_id, grader_id, points, feedback=""):
    sub = Submission.objects.get(pk=submission_id)
    grade, created = Grade.objects.get_or_create(
        submission=sub,
        defaults={"user_id": sub.user_id, "graded_by": grader_id,
                  "points": points, "feedback": feedback},
    )
    if not created:
        grade.points = points
        grade.feedback = feedback
        grade.graded_by = grader_id
        grade.save(update_fields=["points", "feedback", "graded_by", "updated_at"])
    return grade


@transaction.atomic
def release_grade(*, grade_id, releaser_id):
    g = Grade.objects.get(pk=grade_id)
    new = transition(GRADE_TRANSITIONS, g.status, "release")
    if new is None:
        raise ValueError("Cannot release from current state")
    g.status = new
    g.released_by = releaser_id
    from django.utils import timezone
    g.released_at = timezone.now()
    g.save(update_fields=["status", "released_by", "released_at", "updated_at"])
    return g


@transaction.atomic
def change_released_grade(*, grade_id, changer_id, points=None, feedback=None, reason=""):
    g = Grade.objects.get(pk=grade_id)
    if g.status != "released":
        raise ValueError("Grade is not released")
    audit = GradeAudit.objects.create(
        grade=g, changed_by=changer_id,
        old_points=g.points, new_points=points if points is not None else g.points,
        old_feedback=g.feedback, new_feedback=feedback if feedback is not None else g.feedback,
        reason=reason,
    )
    if points is not None:
        g.points = points
    if feedback is not None:
        g.feedback = feedback
    g.save(update_fields=["points", "feedback", "updated_at"])
    return g, audit


# --- Scheduled release (Celery) ---
def release_scheduled_materials():
    from django.utils import timezone
    qs = CourseMaterial.objects.filter(status="scheduled", release_at__lte=timezone.now())
    count = 0
    for m in qs:
        new = transition(MATERIAL_TRANSITIONS, m.status, "release")
        if new:
            m.status = new
            m.save(update_fields=["status", "updated_at"])
            count += 1
    return count


def release_scheduled_assignments():
    from django.utils import timezone
    qs = Assignment.objects.filter(status="scheduled", release_at__lte=timezone.now())
    count = 0
    for a in qs:
        new = transition(ASSIGNMENT_TRANSITIONS, a.status, "release")
        if new:
            a.status = new
            a.save(update_fields=["status", "updated_at"])
            count += 1
    return count
