"""Department metadata and official change services (CFR-DEPT-014, CFR-DEPT-015, CW-DEPT-03)."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.dept.domain.department import (
    transition_official_change,
    validate_official_change_proposal,
)
from modules.dept.models.department import Department
from modules.dept.models.official_changes import OfficialDetailChangeRequest


def update_general_department_info(
    department_code: str,
    description: str | None = None,
) -> Department:
    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )
    if description is not None:
        dept.description = description.strip()
        dept.save(update_fields=["description", "updated_at"])
    return dept


def propose_official_change(
    department_code: str,
    proposer_principal: Any,
    field_name: str,
    new_value: str,
    justification: str,
) -> OfficialDetailChangeRequest:
    validate_official_change_proposal(field_name, new_value, justification)

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    old_val = getattr(dept, field_name, "")
    user_id = str(
        getattr(proposer_principal, "user_id", getattr(proposer_principal, "id", "admin"))
    )

    return OfficialDetailChangeRequest.objects.create(
        department=dept,
        proposed_by_id=user_id,
        field_name=field_name,
        old_value=str(old_val),
        new_value=new_value.strip(),
        justification=justification.strip(),
        status="PENDING",
    )


@transaction.atomic
def decide_official_change(
    change_request_id: str,
    decision: str,  # "APPROVE" or "REJECT"
    hod_principal: Any,
    reason: str = "",
) -> OfficialDetailChangeRequest:
    cr = OfficialDetailChangeRequest.objects.select_for_update().get(id=change_request_id)
    event = decision.upper().strip()

    next_state = transition_official_change(
        current_state=cr.status,
        event=event,
        acting_role="HOD",
    )

    user_id = str(getattr(hod_principal, "user_id", getattr(hod_principal, "id", "hod")))
    cr.status = next_state
    cr.reviewed_by_id = user_id
    cr.review_reason = reason
    cr.reviewed_at = timezone.now()
    cr.save()

    if next_state == "APPROVED":
        dept = Department.objects.select_for_update().get(code=cr.department_id)
        setattr(dept, cr.field_name, cr.new_value)
        dept.save(update_fields=[cr.field_name, "updated_at"])

    return cr
