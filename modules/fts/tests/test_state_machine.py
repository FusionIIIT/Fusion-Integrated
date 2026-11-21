"""Tests for FTS pure state machine."""
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
    assert transition_state(None, ACTION_CREATE_DRAFT) == STATE_DRAFT
    assert transition_state(None, ACTION_CREATE_AND_CIRCULATE) == STATE_CIRCULATED


def test_draft_transitions():
    assert transition_state(STATE_DRAFT, ACTION_EDIT_DRAFT) == STATE_DRAFT
    assert transition_state(STATE_DRAFT, ACTION_DISCARD_DRAFT) == STATE_DISCARDED
    assert transition_state(STATE_DRAFT, ACTION_SEND_INITIAL) == STATE_CIRCULATED


def test_circulated_transitions():
    assert transition_state(STATE_CIRCULATED, ACTION_FORWARD) == STATE_CIRCULATED
    assert transition_state(STATE_CIRCULATED, ACTION_RETURN) == STATE_CIRCULATED
    assert transition_state(STATE_CIRCULATED, ACTION_ARCHIVE) == STATE_ARCHIVED


def test_circulated_file_cannot_be_discarded():
    with pytest.raises(CirculatedFileDeletionProhibitedError):
        transition_state(STATE_CIRCULATED, ACTION_DISCARD_DRAFT)


def test_archived_file_cannot_transition():
    for action in (ACTION_FORWARD, ACTION_RETURN, ACTION_EDIT_DRAFT, ACTION_ARCHIVE):
        with pytest.raises(ArchivedFileModificationProhibitedError):
            transition_state(STATE_ARCHIVED, action)


def test_discarded_file_cannot_transition():
    for action in (ACTION_EDIT_DRAFT, ACTION_SEND_INITIAL, ACTION_FORWARD):
        with pytest.raises(InvalidStateTransitionError):
            transition_state(STATE_DISCARDED, action)
