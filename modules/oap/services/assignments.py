from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.oap.domain import roles
from modules.oap.models import TAAssignment, ThesisSupervisorAssignment
from modules.oap.services.common import need, need_role


def record_thesis_supervisor(
    principal, *, student_user_id: int, supervisor_user_id: int
) -> ThesisSupervisorAssignment:
    need(principal, "oap.thesis_supervisor_assignment.assign")
    need_role(principal, roles.DEPARTMENT_ADMIN)
    if student_user_id == supervisor_user_id:
        raise BadRequestError(
            "A student cannot supervise their own thesis.", code="self_supervision"
        )
    now = timezone.now()
    with transaction.atomic():
        (
            ThesisSupervisorAssignment.objects.select_for_update()
            .filter(student_user_id=student_user_id, superseded_at__isnull=True)
            .update(superseded_at=now)
        )
        return ThesisSupervisorAssignment.objects.create(
            student_user_id=student_user_id,
            supervisor_user_id=supervisor_user_id,
            assigned_by_user_id=principal.user_id,
            assigned_at=now,
        )


def record_ta(
    principal, *, student_user_id: int, course_code: str = "", supervisor_user_id: int | None = None
) -> TAAssignment:
    need(principal, "oap.ta_assignment.assign")
    need_role(principal, roles.DEPARTMENT_ADMIN)
    course_code = (course_code or "").strip()
    if not course_code and supervisor_user_id is None:
        raise BadRequestError(
            "A TA assignment needs a course or subject, a faculty member, or both.",
            code="ta_target_required",
        )
    return TAAssignment.objects.create(
        student_user_id=student_user_id,
        course_code=course_code,
        supervisor_user_id=supervisor_user_id,
        assigned_by_user_id=principal.user_id,
        assigned_at=timezone.now(),
    )
