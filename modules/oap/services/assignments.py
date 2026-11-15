from datetime import date

from core.api.exceptions import BadRequestError
from modules.oap.models.assignments import (
    TeachingAssistantAssignment,
    ThesisSupervisorAssignment,
)


def record_thesis_supervisor_assignment(
    student_user_id: int,
    supervisor_user_id: int,
    department: str,
    assigned_by_user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ThesisSupervisorAssignment:
    """Department Administrator records a thesis supervisor assignment (OA-UC-41, OA-BR-51)."""
    if not student_user_id or not supervisor_user_id or not department:
        raise BadRequestError("student_user_id, supervisor_user_id, and department are required.")

    # Deactivate existing active assignment for this student
    ThesisSupervisorAssignment.objects.filter(
        student_user_id=student_user_id,
        is_active=True,
    ).update(is_active=False)

    return ThesisSupervisorAssignment.objects.create(
        student_user_id=student_user_id,
        supervisor_user_id=supervisor_user_id,
        department=department,
        assigned_by_user_id=assigned_by_user_id,
        is_active=True,
        start_date=start_date,
        end_date=end_date,
    )


def record_ta_assignment(
    student_user_id: int,
    department: str,
    assigned_by_user_id: int,
    ta_supervisor_user_id: int | None = None,
    course_code: str = "",
    semester: str = "",
    year: int | None = None,
) -> TeachingAssistantAssignment:
    """Department Administrator records a TA assignment (OA-UC-42, OA-BR-51, OA-BR-52)."""
    if not student_user_id or not department:
        raise BadRequestError("student_user_id and department are required.")

    # Deactivate existing active assignment for this student if any
    TeachingAssistantAssignment.objects.filter(
        student_user_id=student_user_id,
        course_code=course_code,
        is_active=True,
    ).update(is_active=False)

    return TeachingAssistantAssignment.objects.create(
        student_user_id=student_user_id,
        ta_supervisor_user_id=ta_supervisor_user_id,
        course_code=course_code,
        department=department,
        semester=semester,
        year=year,
        assigned_by_user_id=assigned_by_user_id,
        is_active=True,
    )


def resolve_supervisors_for_student(student_user_id: int) -> tuple[int | None, int | None]:
    """Resolves the thesis supervisor and TA supervisor for a student (OA-BR-52)."""
    thesis_assign = ThesisSupervisorAssignment.objects.filter(
        student_user_id=student_user_id,
        is_active=True,
    ).first()
    ta_assign = TeachingAssistantAssignment.objects.filter(
        student_user_id=student_user_id,
        is_active=True,
    ).first()

    thesis_sup = thesis_assign.supervisor_user_id if thesis_assign else None
    ta_sup = ta_assign.ta_supervisor_user_id if ta_assign else None

    return thesis_sup, ta_sup
