import pytest

from modules.badms.domain.transitions import (
    ARCHIVE_TRANSITIONS,
    RESTORE_TRANSITIONS,
    STORAGE_TRANSITIONS,
    next_state,
)


@pytest.mark.parametrize(("table", "current", "action", "expected"), [
    (ARCHIVE_TRANSITIONS, "Submitted", "hod_approve", "HoD Approved"),
    (ARCHIVE_TRANSITIONS, "HoD Approved", "classify_sensitive",
     "Classified Sensitive / Routed to IT Security"),
    (ARCHIVE_TRANSITIONS, "Classified Sensitive / Routed to IT Security",
     "encrypt", "Sensitive Archive Encrypted"),
    (STORAGE_TRANSITIONS, "Submitted", "approve", "Approved"),
    (RESTORE_TRANSITIONS, "Sensitive Restoration Pending Approval", "approve",
     "Approved for Restoration"),
    (RESTORE_TRANSITIONS, "Approved for Restoration", "restore", "Restored"),
])
def test_documented_workflow_transitions(table, current, action, expected):
    assert next_state(table, current, action) == expected


@pytest.mark.parametrize(("table", "current", "action"), [
    (ARCHIVE_TRANSITIONS, "Submitted", "encrypt"),
    (ARCHIVE_TRANSITIONS, "Sensitive Archive Encrypted", "encrypt"),
    (STORAGE_TRANSITIONS, "Approved", "approve"),
    (RESTORE_TRANSITIONS, "Sensitive Restoration Pending Approval", "restore"),
    (RESTORE_TRANSITIONS, "Restored", "restore"),
])
def test_workflow_rejects_skipped_or_repeated_steps(table, current, action):
    with pytest.raises(ValueError):
        next_state(table, current, action)
