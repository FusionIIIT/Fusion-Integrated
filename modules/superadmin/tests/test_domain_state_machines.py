from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    ARCHIVAL_STATUS_RESTORED,
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_PENDING_IT_HEAD,
    PURGE_STATUS_PURGED,
)
from modules.superadmin.domain.exceptions import (
    ReversibilityExpiredError,
    SelfApprovalForbiddenError,
)
from modules.superadmin.domain.state_machine import ArchivalStateMachine, PurgeStateMachine


def test_archival_state_machine_happy_path() -> None:
    now = datetime(2026, 11, 21, 12, 0)
    deadline = now + timedelta(days=30)
    # Deactivated -> Reversible
    s1 = ArchivalStateMachine.transition(
        "deactivated", "archive", "super_admin", reversible_until=deadline, now=now
    )
    assert s1 == ARCHIVAL_STATUS_REVERSIBLE

    # Reversible -> Restored (within window)
    s2 = ArchivalStateMachine.transition(
        ARCHIVAL_STATUS_REVERSIBLE,
        "restore",
        "super_admin",
        reversible_until=deadline,
        now=now + timedelta(days=10),
    )
    assert s2 == ARCHIVAL_STATUS_RESTORED


def test_archival_state_machine_reversibility_expired() -> None:
    now = datetime(2026, 11, 21, 12, 0)
    deadline = now + timedelta(days=30)
    with pytest.raises(ReversibilityExpiredError):
        ArchivalStateMachine.transition(
            ARCHIVAL_STATUS_REVERSIBLE,
            "restore",
            "super_admin",
            reversible_until=deadline,
            now=now + timedelta(days=31),
        )

    # Expiry sweep transitions to finalized permanent
    s_perm = ArchivalStateMachine.transition(
        ARCHIVAL_STATUS_REVERSIBLE,
        "expire_window",
        "system_scheduler",
        reversible_until=deadline,
        now=now + timedelta(days=31),
    )
    assert s_perm == ARCHIVAL_STATUS_FINALIZED_PERMANENT


def test_purge_state_machine_dual_auth_and_self_approval_blocked() -> None:
    # Super Admin initiates
    s1 = PurgeStateMachine.transition("none", "request_purge", "super_admin")
    assert s1 == PURGE_STATUS_PENDING_IT_HEAD

    # Self-approval prohibited
    with pytest.raises(SelfApprovalForbiddenError):
        PurgeStateMachine.transition(
            PURGE_STATUS_PENDING_IT_HEAD,
            "approve_purge",
            "it_head",
            requester_id=42,
            authorizer_id=42,
        )

    # IT Head approves
    s2 = PurgeStateMachine.transition(
        PURGE_STATUS_PENDING_IT_HEAD, "approve_purge", "it_head", requester_id=42, authorizer_id=99
    )
    assert s2 == PURGE_STATUS_APPROVED

    # Physical execution
    s3 = PurgeStateMachine.transition(PURGE_STATUS_APPROVED, "execute_purge", "super_admin")
    assert s3 == PURGE_STATUS_PURGED
