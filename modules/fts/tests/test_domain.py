"""Domain unit tests for FTS (pure Python, fast)."""
import pytest

from modules.fts.domain import rules
from modules.fts.domain import state_machine as sm


def test_state_machine_legal_transitions():
    assert sm.can_transition(None, sm.EVENT_SAVE_DRAFT)
    assert sm.can_transition(None, sm.EVENT_SUBMIT_CREATE)
    assert sm.can_transition(sm.DRAFT, sm.EVENT_EDIT_DRAFT)
    assert sm.can_transition(sm.DRAFT, sm.EVENT_DISCARD)
    assert sm.can_transition(sm.DRAFT, sm.EVENT_FORWARD)
    assert sm.can_transition(sm.CIRCULATING, sm.EVENT_FORWARD)
    assert sm.can_transition(sm.CIRCULATING, sm.EVENT_RETURN)
    assert sm.can_transition(sm.CIRCULATING, sm.EVENT_ARCHIVE)


def test_terminal_states_reject_all_transitions():
    for term in sm.TERMINAL_STATES:
        assert not sm.can_transition(term, sm.EVENT_FORWARD)
        assert not sm.can_transition(term, sm.EVENT_RETURN)
        assert not sm.can_transition(term, sm.EVENT_ARCHIVE)
        with pytest.raises(sm.InvalidFileStateTransitionError):
            sm.transition(term, sm.EVENT_FORWARD)


def test_illegal_transitions_raise_error():
    with pytest.raises(sm.InvalidFileStateTransitionError):
        sm.transition(sm.DRAFT, sm.EVENT_RETURN)
    with pytest.raises(sm.InvalidFileStateTransitionError):
        sm.transition(sm.CIRCULATING, sm.EVENT_EDIT_DRAFT)


def test_validate_initial_comment_rejects_empty():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_initial_comment("")
    assert exc.value.code == "initial_comment_required"

    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_initial_comment("   ")
    assert exc.value.code == "initial_comment_required"


def test_validate_movement_comment_rejects_empty():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_movement_comment("")
    assert exc.value.code == "movement_comment_required"


def test_validate_forward_recipient_prohibits_self_forward():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_forward_recipient(sender_id=101, receiver_id=101)
    assert exc.value.code == "self_forwarding_prohibited"


def test_validate_return_recipient_requires_previous_sender():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_return_recipient(
            current_holder_id=102,
            target_receiver_id=103,
            expected_previous_sender_id=101,
        )
    assert exc.value.code == "invalid_return_target"


def test_validate_owner_archival_enforces_ownership_and_circulating_state():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_owner_archival(owner_id=100, actor_id=105, current_status="circulating")
    assert exc.value.code == "owner_archival_only"

    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_owner_archival(owner_id=100, actor_id=100, current_status="draft")
    assert exc.value.code == "invalid_archival_state"


def test_validate_operational_role_blocks_admin():
    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_operational_role(is_employee=True, is_system_admin=True)
    assert exc.value.code == "admin_operational_forbidden"

    with pytest.raises(rules.FTSValidationError) as exc:
        rules.validate_operational_role(is_employee=False, is_system_admin=False)
    assert exc.value.code == "employee_required"


def test_domain_rules_positive_paths():
    rules.validate_initial_comment("Valid comment")
    rules.validate_movement_comment("Valid remark")
    rules.validate_forward_recipient(101, 102)
    rules.validate_return_recipient(
        current_holder_id=102,
        target_receiver_id=101,
        expected_previous_sender_id=101,
    )
    rules.validate_owner_archival(101, 101, "circulating")
    rules.validate_operational_role(is_employee=True, is_system_admin=False)


def test_domain_rules_edge_cases():
    with pytest.raises(rules.FTSValidationError) as exc1:
        rules.validate_forward_recipient(101, 0)
    assert exc1.value.code == "recipient_required"

    with pytest.raises(rules.FTSValidationError) as exc2:
        rules.validate_return_recipient(102, 101, None)
    assert exc2.value.code == "no_previous_sender"

    with pytest.raises(rules.FTSValidationError) as exc3:
        rules.validate_return_recipient(101, 101, 101)
    assert exc3.value.code == "self_return_prohibited"


def test_state_machine_transition_positive_and_error():
    assert sm.transition(None, sm.EVENT_SAVE_DRAFT) == sm.DRAFT
    assert sm.transition(None, sm.EVENT_SUBMIT_CREATE) == sm.CIRCULATING
    assert sm.transition(sm.DRAFT, sm.EVENT_EDIT_DRAFT) == sm.DRAFT
    assert sm.transition(sm.DRAFT, sm.EVENT_DISCARD) == sm.DISCARDED
    assert sm.transition(sm.DRAFT, sm.EVENT_FORWARD) == sm.CIRCULATING
    assert sm.transition(sm.CIRCULATING, sm.EVENT_FORWARD) == sm.CIRCULATING
    assert sm.transition(sm.CIRCULATING, sm.EVENT_RETURN) == sm.CIRCULATING
    assert sm.transition(sm.CIRCULATING, sm.EVENT_ARCHIVE) == sm.ARCHIVED

    with pytest.raises(sm.InvalidFileStateTransitionError) as exc:
        sm.transition("unknown_state", sm.EVENT_FORWARD)
    assert "Transition" in str(exc.value)
