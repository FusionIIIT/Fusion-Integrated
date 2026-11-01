from typing import Any

import django.db.transaction
import django.utils.timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.department.domain.department_changes import (
    IllegalTransition,
    next_state,
    split_changes,
)
from modules.department.models import Department, OfficialChangeProposal
from modules.department.selectors.scoping import department_ids_for_role
from modules.department.services.authz import require


def _held(actor, department_id: int) -> Department:
    """Locks and returns the Department if actor has dept_admin role for it."""
    if department_id not in department_ids_for_role(actor, "dept_admin"):
        raise NotFoundError("Department not held by actor as dept_admin")

    with django.db.transaction.atomic():
        department = Department.objects.select_for_update().get(pk=department_id)
        return department

def update_details(*, actor, department_id: int, data: dict[str, Any]) -> tuple[Department, OfficialChangeProposal | None]:
    """Updates department general fields and creates a proposal for official fields."""
    require(actor, "department.department.update")

    with django.db.transaction.atomic():
        try:
            department = _held(actor, department_id)
        except NotFoundError as e:
            raise e

        official_data, general_data = split_changes(data)

        # Save general fields on the department at once
        for key, value in general_data.items():
            setattr(department, key, value)
        department.save()

        proposal = None
        if official_data:
            # Create a proposal holding only official fields
            proposal = OfficialChangeProposal.objects.create(
                department=department,
                proposed_by_user_id=actor.user_id,
                changes=official_data,
            )
            # Department's official fields stay unchanged

        return department, proposal

def decide_change(*, actor, proposal_id: int, outcome: str) -> OfficialChangeProposal:
    """Approves or rejects an official change proposal."""
    require(actor, "department.official_change.approve")

    with django.db.transaction.atomic():
        try:
            proposal = OfficialChangeProposal.objects.select_for_update().get(pk=proposal_id)
        except OfficialChangeProposal.DoesNotExist:
            raise NotFoundError("Official change proposal not found")

        # Check if actor has HOD role for the department associated with the proposal
        department_id = proposal.department_id
        if department_id not in department_ids_for_role(actor, "hod"):
            raise NotFoundError("Actor is not HOD for this department")

        # Compute the event based on outcome
        if outcome == "approved":
            event = "approve"
        elif outcome == "rejected":
            event = "reject"
        else:
            raise BadRequestError("Invalid outcome provided.")

        # Determine next state and handle transitions
        current_state = proposal.state
        try:
            next_state_str = next_state(current_state, event)
        except IllegalTransition:
            raise ConflictError("Invalid transition attempted.", code="illegal_transition")

        if next_state_str == "approved":
            # Approve: Set state, decided_by_user_id, decided_at. Set each proposed field on the department and save.
            department = proposal.department
            for field, value in proposal.changes.items():
                setattr(department, field, value)
            department.save()

            proposal.state = "approved"
            proposal.decided_by_user_id = actor.user_id
            proposal.decided_at = django.utils.timezone.now()
            proposal.save()
            return proposal

        if next_state_str == "rejected":
            # Reject: Set state, decided_by_user_id, decided_at.
            proposal.state = "rejected"
            proposal.decided_by_user_id = actor.user_id
            proposal.decided_at = django.utils.timezone.now()
            proposal.save()
            return proposal

        # Any other outcome raises BadRequestError
        raise BadRequestError("Invalid outcome provided.")
