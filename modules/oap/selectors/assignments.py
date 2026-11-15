from django.db.models import QuerySet

from modules.oap.models.assignments import (
    TeachingAssistantAssignment,
    ThesisSupervisorAssignment,
)


def get_thesis_supervisors_for_student(student_user_id: int) -> QuerySet[ThesisSupervisorAssignment]:
    return ThesisSupervisorAssignment.objects.filter(student_user_id=student_user_id, is_active=True)


def get_ta_assignments_for_student(student_user_id: int) -> QuerySet[TeachingAssistantAssignment]:
    return TeachingAssistantAssignment.objects.filter(student_user_id=student_user_id, is_active=True)


def get_all_thesis_assignments(department: str | None = None) -> QuerySet[ThesisSupervisorAssignment]:
    qs = ThesisSupervisorAssignment.objects.all()
    if department:
        qs = qs.filter(department=department)
    return qs


def get_all_ta_assignments(department: str | None = None) -> QuerySet[TeachingAssistantAssignment]:
    qs = TeachingAssistantAssignment.objects.all()
    if department:
        qs = qs.filter(department=department)
    return qs
