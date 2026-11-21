from django.db import transaction

from modules.oap.models import SupervisorAssignment, TAAssignment
from modules.oap.services.common import ServiceError, department_of


def _check_same_department(student_id, actor_id):
    """OA-BR-51: an administrator records only for students of their department."""
    actor_department = department_of(actor_id)
    if not actor_department or actor_department != department_of(student_id):
        raise ServiceError("You can only record assignments for your own department.")


def record_supervisor(student_id, faculty_id, actor_id, decision_reference=""):
    """OA-UC-41."""
    _check_same_department(student_id, actor_id)
    with transaction.atomic():
        assignment, _ = SupervisorAssignment.objects.update_or_create(
            student_id=student_id,
            defaults={
                "faculty_id": faculty_id,
                "assigned_by_id": actor_id,
                "decision_reference": decision_reference,
            },
        )
    return assignment


def record_ta(student_id, actor_id, course_code="", faculty_id=None):
    """OA-UC-42. A TA assignment names a course, a faculty member, or both."""
    if not course_code and faculty_id is None:
        raise ServiceError("A course code or a faculty member is required.")
    _check_same_department(student_id, actor_id)
    return TAAssignment.objects.create(
        student_id=student_id,
        course_code=course_code,
        faculty_id=faculty_id,
        assigned_by_id=actor_id,
    )


def resolve_supervisors(student_id):
    """Return (thesis_supervisor_id or None, ta_supervisor_id or None).

    A course-only TA assignment does not give a TA Supervisor (OA-UC-42 note).
    """
    thesis = (
        SupervisorAssignment.objects.filter(student_id=student_id)
        .values_list("faculty_id", flat=True)
        .first()
    )
    # TAAssignment is ordered newest first.
    ta = (
        TAAssignment.objects.filter(student_id=student_id, faculty_id__isnull=False)
        .values_list("faculty_id", flat=True)
        .first()
    )
    return thesis, ta
