"""Feedback services and workflow execution (CFR-DEPT-007, CFR-DEPT-008, CW-DEPT-02)."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from modules.dept.domain.feedback import transition_feedback, validate_feedback_submission
from modules.dept.models.department import Department
from modules.dept.models.feedback import Feedback


def submit_feedback(
    department_code: str,
    submitter_principal: Any,
    category: str,
    title: str,
    description: str,
) -> Feedback:
    validate_feedback_submission(title, description, category)

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    user_id = str(
        getattr(submitter_principal, "user_id", getattr(submitter_principal, "id", "anonymous"))
    )
    roles = getattr(submitter_principal, "roles", ["student"])
    submitter_role = "FACULTY" if "faculty" in roles else "STUDENT"

    return Feedback.objects.create(
        department=dept,
        submitted_by_id=user_id,
        submitter_role=submitter_role,
        category=category.upper().strip(),
        title=title.strip(),
        description=description.strip(),
        status="NEW",
    )


def review_feedback_initial(
    feedback_id: str,
    admin_principal: Any,
    admin_remarks: str = "",
) -> Feedback:
    fb = Feedback.objects.get(id=feedback_id)
    next_state = transition_feedback(
        current_state=fb.status,
        event="START_REVIEW",
        acting_role="DEPT_ADMIN",
    )
    user_id = str(getattr(admin_principal, "user_id", getattr(admin_principal, "id", "admin")))
    fb.status = next_state
    fb.admin_remarks = admin_remarks
    fb.reviewed_by_admin_id = user_id
    fb.reviewed_at = timezone.now()
    fb.save()
    return fb


def resolve_or_close_feedback(
    feedback_id: str,
    action: str,  # "RESOLVE" or "CLOSE"
    actor_principal: Any,
    remarks: str = "",
) -> Feedback:
    fb = Feedback.objects.get(id=feedback_id)
    event = action.upper().strip()

    roles = set(getattr(actor_principal, "roles", []))
    acting_role = "HOD" if "HOD" in roles else "DEPT_ADMIN"

    next_state = transition_feedback(
        current_state=fb.status,
        event=event,
        acting_role=acting_role,
    )

    user_id = str(getattr(actor_principal, "user_id", getattr(actor_principal, "id", "admin")))
    fb.status = next_state
    fb.terminal_by_id = user_id
    fb.terminal_by_role = acting_role
    fb.terminal_remarks = remarks
    fb.terminal_at = timezone.now()
    fb.save()
    return fb
