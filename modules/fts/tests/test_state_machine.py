"""Tests for FTS pure state machine.

Validates BR-FTS-001, BR-FTS-007, BR-FTS-008, AFR-FTS-014, AFR-FTS-042, AFR-FTS-043.
"""
from __future__ import annotations

import pytest

from modules.fts.domain.errors import (
    ArchivedFileModificationProhibitedError,
    CirculatedFileDeletionProhibitedError,
    InvalidStateTransitionError,
)
from modules.fts.domain.state_machine import (
    ACTION_ARCHIVE,
    ACTION_CREATE_AND_CIRCULATE,
    ACTION_CREATE_DRAFT,
    ACTION_DISCARD_DRAFT,
    ACTION_EDIT_DRAFT,
    ACTION_FORWARD,
    ACTION_RETURN,
    ACTION_SEND_INITIAL,
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
    transition_state,
)


def test_creation_transitions():
    """BR-FTS-001 & AFR-FTS-014: Initial creation into DRAFT or CIRCULATED."""
    assert transition_state(None, ACTION_CREATE_DRAFT) == STATE_DRAFT
    assert transition_state(None, ACTION_CREATE_AND_CIRCULATE) == STATE_CIRCULATED


def test_invalid_action_on_none_state():
    """BR-FTS-001: Invalid actions on uncreated file raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError, match="Cannot perform"):
        transition_state(None, ACTION_FORWARD)


def test_draft_transitions():
    """BR-FTS-007 & BR-FTS-008: Valid transitions from DRAFT state."""
    assert transition_state(STATE_DRAFT, ACTION_EDIT_DRAFT) == STATE_DRAFT
    assert transition_state(STATE_DRAFT, ACTION_DISCARD_DRAFT) == STATE_DISCARDED
    assert transition_state(STATE_DRAFT, ACTION_SEND_INITIAL) == STATE_CIRCULATED


def test_invalid_action_on_draft():
    """BR-FTS-007: Non-permitted actions on DRAFT file raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError, match="not valid on a DRAFT file"):
        transition_state(STATE_DRAFT, ACTION_RETURN)
    with pytest.raises(InvalidStateTransitionError, match="not valid on a DRAFT file"):
        transition_state(STATE_DRAFT, ACTION_ARCHIVE)


def test_circulated_transitions():
    """BR-FTS-001 & AFR-FTS-042: Valid transitions from CIRCULATED state."""
    assert transition_state(STATE_CIRCULATED, ACTION_FORWARD) == STATE_CIRCULATED
    assert transition_state(STATE_CIRCULATED, ACTION_RETURN) == STATE_CIRCULATED
    assert transition_state(STATE_CIRCULATED, ACTION_ARCHIVE) == STATE_ARCHIVED


def test_invalid_action_on_circulated():
    """AFR-FTS-043: Non-permitted actions on CIRCULATED file raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError, match="not valid on a CIRCULATED file"):
        transition_state(STATE_CIRCULATED, ACTION_EDIT_DRAFT)
    with pytest.raises(InvalidStateTransitionError, match="not valid on a CIRCULATED file"):
        transition_state(STATE_CIRCULATED, ACTION_CREATE_DRAFT)


def test_circulated_file_cannot_be_discarded():
    """BR-FTS-008: Circulated file cannot be deleted or discarded."""
    with pytest.raises(CirculatedFileDeletionProhibitedError):
        transition_state(STATE_CIRCULATED, ACTION_DISCARD_DRAFT)


def test_archived_file_cannot_transition():
    """AFR-FTS-042 & AFR-FTS-043: Archived files cannot undergo further transitions."""
    for action in (ACTION_FORWARD, ACTION_RETURN, ACTION_EDIT_DRAFT, ACTION_ARCHIVE):
        with pytest.raises(ArchivedFileModificationProhibitedError):
            transition_state(STATE_ARCHIVED, action)


def test_discarded_file_cannot_transition():
    """BR-FTS-008: Discarded files are terminal and cannot be transitioned."""
    for action in (ACTION_EDIT_DRAFT, ACTION_SEND_INITIAL, ACTION_FORWARD):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(STATE_DISCARDED, action)


def test_unknown_state_raises_error():
    """Verify error handling on unknown state strings."""
    with pytest.raises(InvalidStateTransitionError, match="Unknown current file state"):
        transition_state("INVALID_STATE", ACTION_FORWARD)
