"""Time-bound VMS role assignments (VMS-BR-025, VMS-BR-026).

Super Admin hands these out; reassignment is immediate, so a row that is
inactive or outside its validity window reads as not holding the role at all.
A host with NO host row is an ordinary faculty member and is enabled by
default — only an explicit disable blocks (VMS-BR-026).
"""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import VmsRoleAssignment
from modules.vms.services.errors import (
    HostDisabledError,
    SecurityMisconfiguredError,
)


def _in_window(row: VmsRoleAssignment, at=None) -> bool:
    at = at or timezone.now()
    if row.valid_from and at < row.valid_from:
        return False
    if row.valid_to and at > row.valid_to:
        return False
    return True


def active_assignment(user_id: int, role: str) -> VmsRoleAssignment | None:
    """The one live assignment for this user and role, if any."""
    rows = (VmsRoleAssignment.objects
            .filter(user_id=user_id, role=role, is_active=True))
    for row in rows:
        if _in_window(row):
            return row
    return None


def require_security(actor, *, gate_code: str = "",
                     zone_code: str = "") -> VmsRoleAssignment:
    """VMS-BR-025: a misconfigured security person (no active row, expired,
    or scoped to other zones/gates) invalidates the visit they record.

    Called AFTER the visit row exists on the check-in path so the failure
    leaves an INVALIDATED visit behind rather than a silent no-op.
    """
    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        raise SecurityMisconfiguredError("No actor on this request.")
    row = active_assignment(user_id, "SECURITY")
    if row is None:
        raise SecurityMisconfiguredError(
            f"user {user_id} has no active security assignment.")
    if row.gate_code and gate_code and row.gate_code != gate_code:
        raise SecurityMisconfiguredError(
            f"user {user_id} is not assigned to gate {gate_code}.")
    if row.zone_codes and zone_code and zone_code not in row.zone_codes:
        raise SecurityMisconfiguredError(
            f"user {user_id} is not assigned to zone {zone_code}.")
    return row


def require_admin(actor) -> VmsRoleAssignment | None:
    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        raise SecurityMisconfiguredError("No actor on this request.")
    row = active_assignment(user_id, "ADMIN")
    if row is None:
        raise SecurityMisconfiguredError(
            f"user {user_id} has no active admin assignment.")
    return row


def is_host_enabled(user_id: int) -> bool:
    """VMS-BR-026: an explicitly disabled (or expired) host is not valid
    for check-in. No row at all means an ordinary, enabled faculty host."""
    rows = VmsRoleAssignment.objects.filter(user_id=user_id, role="HOST")
    for row in rows:
        if not row.is_active or not _in_window(row):
            return False
    return True


def require_host_enabled(user_id: int) -> None:
    if not is_host_enabled(user_id):
        raise HostDisabledError(
            f"Host {user_id} is disabled or outside their assignment window.")
