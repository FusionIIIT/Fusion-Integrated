"""Role management (BR-MMS-002/003/004/006/007; UC-001).

Not workflow-grounded: an isolated service with DB-enforced cardinality.
Exactly one active Caretaker and exactly one active Warden at a time.
"""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.mms.models import RoleAssignment


def current_assignments():
    return RoleAssignment.objects.all().order_by("designation", "-effective_from")


def assign(
    actor, designation: str, employee_user_id: int, effective_from, effective_until=None
) -> RoleAssignment:
    """Mess Admin assigns/reassigns. Enforces exactly one active per
    designation (BR-MMS-003/004); mid-cycle reassignment is immediate
    (BR-MMS-006)."""
    from modules.mms.services import authz

    authz.require(actor, "mms.role.assign")
    if designation not in ("caretaker", "warden"):
        raise ConflictError("Designation must be 'caretaker' or 'warden'.")
    with transaction.atomic():
        # Deactivate any currently active assignment of this designation
        # (BR-MMS-006: immediate mid-cycle reassignment).
        RoleAssignment.objects.filter(designation=designation, is_active=True).update(
            is_active=False
        )
        return RoleAssignment.objects.create(
            designation=designation,
            employee_user_id=employee_user_id,
            effective_from=effective_from,
            effective_until=effective_until,
            is_active=True,
            assigned_by_user_id=actor.user_id,
        )
