"""Write authority, stated once. Every service write path calls it (BR-EL-036).

The unit head may not review their own request and nobody may sanction their
own: the self-approval guard is structural here rather than a rule each
endpoint has to remember.
"""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError
from modules.leave.domain import state_machine as sm

P_REVIEW = "leave.request.review"
P_APPROVE = "leave.request.approve"
P_RECORDS = "leave.record.view"


def has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def actor_kind(actor, *, row=None) -> str:
    """Which lane of the state machine this caller is in."""
    if actor is None:
        return sm.SYSTEM

    user_id = getattr(actor, "user_id", None)
    if row is not None and user_id == row.user_id:
        # BR-EL-020: the Director deciding their own leave is the one case where
        # the applicant and the authority are the same person.
        if row.status == sm.AWAITING_DIRECTOR_SELF_SANCTION:
            return sm.DIRECTOR
        return sm.EMPLOYEE

    if row is not None and _is_nominated_substitute(row, user_id):
        return sm.SUBSTITUTE

    if row is not None and row.status.startswith("resumption"):
        return sm.SANCTIONING_AUTHORITY if has(actor, P_APPROVE) \
            or getattr(actor, "active_role", "") else sm.SYSTEM

    if (row is not None and row.status in _ESTABLISHMENT_STATES
            and has(actor, P_REVIEW, P_RECORDS)):
        return sm.ESTABLISHMENT

    if has(actor, P_APPROVE):
        return sm.SANCTIONING_AUTHORITY
    if has(actor, P_REVIEW):
        return sm.UNIT_HEAD
    return sm.EMPLOYEE


_ESTABLISHMENT_STATES = frozenset({
    sm.AWAITING_ESTABLISHMENT,
    sm.CANCELLATION_AWAITING_ESTABLISHMENT,
    sm.EXTENSION_AWAITING_ESTABLISHMENT,
})


def _is_nominated_substitute(row, user_id: int | None) -> bool:
    """Pending, accepted or declined: a respondent is still the substitute."""
    if user_id is None or row.pk is None:
        return False
    return row.substitute_assignments.filter(
        substitute_user_id=user_id,
        state__in=("pending", "accepted", "declined")).exists()


def require(actor, *codes: str) -> None:
    """Admit the actor, or refuse with a sentence they can act on."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    if not has(actor, *codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.", code="permission_denied")


def is_acting_for(row, actor) -> bool:
    """Whether this actor owns the row, which lands them in the employee lane."""
    return row is not None and getattr(actor, "user_id", None) == row.user_id
