"""Declarative state machine for File Tracking System lifecycle (framework-free)."""


from modules.filetracking.domain.entities import FileEvent, FileStatus
from modules.filetracking.domain.errors import (
    DraftDiscardError,
    FileArchivedError,
    StateTransitionError,
)

# Declarative transitions: (current_state, event) -> (next_state, allowed_actor_roles)
# None as next_state represents deletion of the draft.
TRANSITIONS: dict[tuple[str, str], tuple[str | None, set[str]]] = {
    # Draft Phase (BW-FTS-05..08 / CW-FTS-02)
    (FileStatus.DRAFT, FileEvent.UPDATE_DRAFT): (FileStatus.DRAFT, {"OWNER"}),
    (FileStatus.DRAFT, FileEvent.DISCARD_DRAFT): (None, {"OWNER"}),
    (FileStatus.DRAFT, FileEvent.SUBMIT_INITIAL): (FileStatus.CIRCULATING, {"OWNER"}),

    # Active Circulation Phase (BW-FTS-01..03 / CW-FTS-01)
    (FileStatus.CIRCULATING, FileEvent.FORWARD): (FileStatus.CIRCULATING, {"CURRENT_HOLDER"}),
    (FileStatus.CIRCULATING, FileEvent.RETURN): (FileStatus.CIRCULATING, {"CURRENT_HOLDER"}),

    # Lifecycle Closing Phase (BW-FTS-04 / CW-FTS-01)
    (FileStatus.CIRCULATING, FileEvent.ARCHIVE): (FileStatus.ARCHIVED, {"OWNER"}),
}


def can_transition(current_state: str, event: str, actor_role: str) -> bool:
    """Check whether a transition is permitted under the state machine."""
    key = (current_state, event)
    if key not in TRANSITIONS:
        return False
    _, allowed_roles = TRANSITIONS[key]
    return actor_role in allowed_roles


def get_next_state(current_state: str, event: str, actor_role: str) -> str | None:
    """Calculate and return the next state or raise a domain error."""
    if current_state == FileStatus.ARCHIVED:
        raise FileArchivedError(
            "Archived files are permanently closed and cannot undergo further state transitions."
        )

    if event == FileEvent.DISCARD_DRAFT and current_state != FileStatus.DRAFT:
        raise DraftDiscardError(
            "Circulated files cannot be discarded. Only uncirculated drafts may be discarded."
        )

    key = (current_state, event)
    if key not in TRANSITIONS:
        raise StateTransitionError(
            f"Transition from state '{current_state}' via event '{event}' is illegal."
        )

    next_state, allowed_roles = TRANSITIONS[key]
    if actor_role not in allowed_roles:
        raise StateTransitionError(
            f"Actor with role '{actor_role}' is not authorized to trigger '{event}' "
            f"on state '{current_state}'."
        )

    return next_state
