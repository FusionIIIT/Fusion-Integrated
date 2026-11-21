from __future__ import annotations

from datetime import datetime

from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    ARCHIVAL_STATUS_RESTORED,
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_EXPIRED,
    PURGE_STATUS_PENDING_IT_HEAD,
    PURGE_STATUS_PURGED,
    PURGE_STATUS_REJECTED,
)
from modules.superadmin.domain.exceptions import (
    InvalidStateTransitionError,
    ReversibilityExpiredError,
    SelfApprovalForbiddenError,
)

ARCHIVAL_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("deactivated", "archive", "super_admin"): ARCHIVAL_STATUS_REVERSIBLE,
    (ARCHIVAL_STATUS_REVERSIBLE, "restore", "super_admin"): ARCHIVAL_STATUS_RESTORED,
    (
        ARCHIVAL_STATUS_REVERSIBLE,
        "expire_window",
        "system_scheduler",
    ): ARCHIVAL_STATUS_FINALIZED_PERMANENT,
}

PURGE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "request_purge", "super_admin"): PURGE_STATUS_PENDING_IT_HEAD,
    (PURGE_STATUS_PENDING_IT_HEAD, "approve_purge", "it_head"): PURGE_STATUS_APPROVED,
    (PURGE_STATUS_PENDING_IT_HEAD, "reject_purge", "it_head"): PURGE_STATUS_REJECTED,
    (PURGE_STATUS_PENDING_IT_HEAD, "expire_request", "system_scheduler"): PURGE_STATUS_EXPIRED,
    (PURGE_STATUS_APPROVED, "execute_purge", "super_admin"): PURGE_STATUS_PURGED,
}


class ArchivalStateMachine:
    @staticmethod
    def transition(
        current_state: str, action: str, actor: str, *, reversible_until: datetime, now: datetime
    ) -> str:
        key = (current_state, action, actor)
        if key not in ARCHIVAL_TRANSITIONS:
            raise InvalidStateTransitionError(current_state, action, "user_archival")
        next_state = ARCHIVAL_TRANSITIONS[key]
        if action == "restore" and now > reversible_until:
            raise ReversibilityExpiredError(reversible_until.isoformat())
        return next_state


class PurgeStateMachine:
    @staticmethod
    def transition(
        current_state: str,
        action: str,
        actor: str,
        *,
        requester_id: int | None = None,
        authorizer_id: int | None = None,
    ) -> str:
        key = (current_state, action, actor)
        if key not in PURGE_TRANSITIONS:
            raise InvalidStateTransitionError(current_state, action, "purge_request")
        if action in {"approve_purge", "reject_purge"} and (
            requester_id is not None
            and authorizer_id is not None
            and requester_id == authorizer_id
        ):
            raise SelfApprovalForbiddenError()
        return PURGE_TRANSITIONS[key]
