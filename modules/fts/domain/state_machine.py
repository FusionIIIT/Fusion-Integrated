"""Pure Python state machine for the FTS file lifecycle."""
from __future__ import annotations

from modules.fts.domain.errors import (
    ArchivedFileModificationProhibitedError,
    CirculatedFileDeletionProhibitedError,
    InvalidStateTransitionError,
)

STATE_DRAFT = "DRAFT"
STATE_CIRCULATED = "CIRCULATED"
STATE_ARCHIVED = "ARCHIVED"
STATE_DISCARDED = "DISCARDED"

VALID_STATES = {STATE_DRAFT, STATE_CIRCULATED, STATE_ARCHIVED, STATE_DISCARDED}

ACTION_CREATE_DRAFT = "CREATE_DRAFT"
ACTION_CREATE_AND_CIRCULATE = "CREATE_AND_CIRCULATE"
ACTION_EDIT_DRAFT = "EDIT_DRAFT"
ACTION_DISCARD_DRAFT = "DISCARD_DRAFT"
ACTION_SEND_INITIAL = "SEND_INITIAL"
ACTION_FORWARD = "FORWARD"
ACTION_RETURN = "RETURN"
ACTION_ARCHIVE = "ARCHIVE"


def transition_state(current_state: str | None, action: str) -> str:
    """Computes the target file status from the current status and requested action."""
    if current_state == STATE_ARCHIVED:
        raise ArchivedFileModificationProhibitedError(
            "Archived files are permanently closed and cannot be modified or transitioned. "
            "Create a new file if further action is required."
        )

    if current_state == STATE_DISCARDED:
        raise InvalidStateTransitionError(
            "Discarded drafts are terminal and cannot be modified or transitioned. "
            "Create a new draft if you wish to restart this file."
        )

    if current_state is None:
        if action == ACTION_CREATE_DRAFT:
            return STATE_DRAFT
        if action == ACTION_CREATE_AND_CIRCULATE:
            return STATE_CIRCULATED
        raise InvalidStateTransitionError(
            f"Cannot perform {action} on non-existent file. Create the file first."
        )

    if current_state == STATE_DRAFT:
        if action == ACTION_EDIT_DRAFT:
            return STATE_DRAFT
        if action == ACTION_DISCARD_DRAFT:
            return STATE_DISCARDED
        if action == ACTION_SEND_INITIAL:
            return STATE_CIRCULATED
        raise InvalidStateTransitionError(
            f"Action {action} is not valid on a DRAFT file. "
            "Choose either to edit, discard, or circulate the draft."
        )

    if current_state == STATE_CIRCULATED:
        if action == ACTION_DISCARD_DRAFT:
            raise CirculatedFileDeletionProhibitedError(
                "A file cannot be discarded or deleted once submitted and circulated. "
                "Forward or return the file to the appropriate handler instead."
            )
        if action in (ACTION_FORWARD, ACTION_RETURN):
            return STATE_CIRCULATED
        if action == ACTION_ARCHIVE:
            return STATE_ARCHIVED
        raise InvalidStateTransitionError(
            f"Action {action} is not valid on a CIRCULATED file. "
            "Forward, return, or archive the file as permitted."
        )

    raise InvalidStateTransitionError(
        f"Unknown current file state: {current_state}. Verify the file state before proceeding."
    )
