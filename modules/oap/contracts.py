"""OAP public surface. The ONLY module entry other modules may import.

Clean, decoupled contract interface for cross-boundary queries.
"""

from __future__ import annotations

from modules.oap.domain import constants as c
from modules.oap.models import (
    NoDuesRequest,
    StudentLeaveApplication,
    TeachingAssistantAssignment,
    ThesisSupervisorAssignment,
)


def is_no_dues_finalized(user_id: int) -> bool:
    """Returns True if the student has a finalized no-dues clearance certificate."""
    return NoDuesRequest.objects.filter(
        user_id=user_id,
        status=c.NODUES_FINALIZED,
    ).exists()


def get_student_approved_leave_count(user_id: int) -> int:
    """Returns count of approved leave requests for the student."""
    return StudentLeaveApplication.objects.filter(
        user_id=user_id,
        status=c.LEAVE_APPROVED,
    ).count()


def get_student_active_supervisors(student_user_id: int) -> dict[str, int | None]:
    """Returns the student's active thesis supervisor and TA supervisor IDs."""
    thesis = ThesisSupervisorAssignment.objects.filter(
        student_user_id=student_user_id,
        is_active=True,
    ).first()
    ta = TeachingAssistantAssignment.objects.filter(
        student_user_id=student_user_id,
        is_active=True,
    ).first()

    return {
        "thesis_supervisor_user_id": thesis.supervisor_user_id if thesis else None,
        "ta_supervisor_user_id": ta.ta_supervisor_user_id if ta else None,
    }
