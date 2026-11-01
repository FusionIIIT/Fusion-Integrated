"""File state machine and lifecycle transitions for FTS.

Pure Python — no framework imports allowed in domain/.
Implements BR-FTS-003, BR-FTS-005, BR-FTS-012, and workflows BW-FTS-01..08.
"""
from enum import StrEnum

from .errors import DraftBoundaryViolationError, FileArchivedError


class FileLifecycleState(StrEnum):
    DRAFT = "draft"
    CIRCULATED = "circulated"
    ARCHIVED = "archived"


class MovementType(StrEnum):
    CREATION = "creation"
    FORWARD = "forward"
    RETURN = "return"
    ARCHIVAL = "archival"


ALLOWED_TRANSITIONS: dict[FileLifecycleState, set[FileLifecycleState]] = {
    FileLifecycleState.DRAFT: {
        FileLifecycleState.DRAFT,        # edit draft
        FileLifecycleState.CIRCULATED,   # initial send / circulation
    },
    FileLifecycleState.CIRCULATED: {
        FileLifecycleState.CIRCULATED,   # onward forward / return
        FileLifecycleState.ARCHIVED,     # owner archives completed file
    },
    FileLifecycleState.ARCHIVED: set(),  # terminal state — no further transitions
}


def assert_can_transition(from_state: FileLifecycleState, to_state: FileLifecycleState) -> None:
    """Validate that moving from from_state to to_state is valid."""
    if from_state == FileLifecycleState.ARCHIVED:
        raise FileArchivedError(
            "Archived files are permanent read-only records and cannot transition "
            "or be modified (BR-FTS-012)."
        )
    allowed = ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise DraftBoundaryViolationError(
            f"Invalid file lifecycle transition from {from_state.value} to {to_state.value}."
        )


def assert_can_discard_draft(state: FileLifecycleState) -> None:
    """Validate that a file can be discarded (BR-FTS-005)."""
    if state != FileLifecycleState.DRAFT:
        raise DraftBoundaryViolationError(
            f"Only pre-circulation draft files can be discarded; file in state {state.value} "
            "cannot be deleted (BR-FTS-005)."
        )


def assert_can_edit_draft(state: FileLifecycleState) -> None:
    """Validate that draft contents can be edited before submission."""
    if state != FileLifecycleState.DRAFT:
        raise DraftBoundaryViolationError(
            f"Draft edit is permitted only before submission; current state is {state.value} "
            "(BR-FTS-005)."
        )


def assert_can_forward_or_return(state: FileLifecycleState) -> None:
    """Validate that file can undergo movement (BR-FTS-006, BR-FTS-012)."""
    if state == FileLifecycleState.ARCHIVED:
        raise FileArchivedError(
            "Archived files cannot be forwarded or returned (BR-FTS-012)."
        )
    if state not in (FileLifecycleState.DRAFT, FileLifecycleState.CIRCULATED):
        raise DraftBoundaryViolationError(
            f"File in state {state.value} cannot be forwarded or returned."
        )


def assert_can_archive(state: FileLifecycleState, user_id: int, owner_id: int) -> None:
    """Validate archival rule (BR-FTS-012, AFR-FTS-042, AFR-FTS-043)."""
    if user_id != owner_id:
        from .errors import ArchivalNotAllowedError
        raise ArchivalNotAllowedError(
            f"Only the file owner (user_id={owner_id}) can archive this file "
            f"(user_id={user_id}) (BR-FTS-012)."
        )
    if state == FileLifecycleState.DRAFT:
        from .errors import ArchivalNotAllowedError
        raise ArchivalNotAllowedError(
            "Pre-circulation draft files cannot be archived; only circulated completed files "
            "can be archived (BR-FTS-012)."
        )
    if state == FileLifecycleState.ARCHIVED:
        raise FileArchivedError("File is already archived.")
