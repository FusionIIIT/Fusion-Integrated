# Tests for leave application state transitions (BR-EL-022, BR-EL-023, BR-EL-034)
import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.constants import (
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
)
from modules.leave.domain.state_machine import (
    ACTOR_APPLICANT,
    ACTOR_APPROVER,
    validate_transition,
)


def test_legal_transitions():
    """Approver can approve or reject; applicant can withdraw or cancel."""
    t1 = validate_transition(STATUS_PENDING, STATUS_APPROVED, ACTOR_APPROVER)
    assert t1.frm == STATUS_PENDING and t1.to == STATUS_APPROVED

    t2 = validate_transition(STATUS_PENDING, STATUS_REJECTED, ACTOR_APPROVER)
    assert t2.frm == STATUS_PENDING and t2.to == STATUS_REJECTED

    t3 = validate_transition(STATUS_PENDING, STATUS_WITHDRAWN, ACTOR_APPLICANT)
    assert t3.frm == STATUS_PENDING and t3.to == STATUS_WITHDRAWN

    t4 = validate_transition(STATUS_APPROVED, STATUS_CANCELLED, ACTOR_APPLICANT)
    assert t4.frm == STATUS_APPROVED and t4.to == STATUS_CANCELLED


def test_terminal_state_refuses_modification():
    """Terminal states (REJECTED, WITHDRAWN, CANCELLED) cannot transition anywhere."""
    with pytest.raises(ConflictError, match="terminal state"):
        validate_transition(STATUS_REJECTED, STATUS_APPROVED, ACTOR_APPROVER)

    with pytest.raises(ConflictError, match="terminal state"):
        validate_transition(STATUS_WITHDRAWN, STATUS_APPROVED, ACTOR_APPROVER)

    with pytest.raises(ConflictError, match="terminal state"):
        validate_transition(STATUS_CANCELLED, STATUS_APPROVED, ACTOR_APPROVER)


def test_illegal_transitions():
    """Direct jump from PENDING to CANCELLED or APPROVED to REJECTED is forbidden."""
    with pytest.raises(ConflictError, match="Illegal status transition"):
        validate_transition(STATUS_PENDING, STATUS_CANCELLED, ACTOR_APPLICANT)

    with pytest.raises(ConflictError, match="Illegal status transition"):
        validate_transition(STATUS_APPROVED, STATUS_REJECTED, ACTOR_APPROVER)


def test_actor_permission_enforcement():
    """Applicant cannot approve; approver cannot withdraw."""
    with pytest.raises(ConflictError, match="cannot move leave"):
        validate_transition(STATUS_PENDING, STATUS_APPROVED, ACTOR_APPLICANT)

    with pytest.raises(ConflictError, match="cannot move leave"):
        validate_transition(STATUS_PENDING, STATUS_WITHDRAWN, ACTOR_APPROVER)
