"""
Pure Python Indent State Machine & Transitions (PSM Domain).
No Django imports allowed.
"""

from enum import Enum
from typing import Union


class IndentState(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    STOCK_CHECKED = "STOCK_CHECKED"
    DEPT_REVIEWED = "DEPT_REVIEWED"
    HEAD_RECOMMENDED = "HEAD_RECOMMENDED"
    AWAITING_FINAL_APPROVAL = "AWAITING_FINAL_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


# State transition validation map covering Basis and Composite Workflows
# (BW-PSM-01, BW-PSM-02, BW-PSM-03, BW-PSM-07, CW-PSM-01)
TRANSITION_MATRIX: dict[str, list[str]] = {
    IndentState.DRAFT.value: [
        IndentState.SUBMITTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.SUBMITTED.value: [
        IndentState.STOCK_CHECKED.value,
        IndentState.REJECTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.STOCK_CHECKED.value: [
        IndentState.DEPT_REVIEWED.value,
        IndentState.REJECTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.DEPT_REVIEWED.value: [
        IndentState.HEAD_RECOMMENDED.value,
        IndentState.REJECTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.HEAD_RECOMMENDED.value: [
        IndentState.AWAITING_FINAL_APPROVAL.value,
        IndentState.REJECTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.AWAITING_FINAL_APPROVAL.value: [
        IndentState.APPROVED.value,
        IndentState.REJECTED.value,
        IndentState.WITHDRAWN.value,
    ],
    IndentState.APPROVED.value: [],
    IndentState.REJECTED.value: [],
    IndentState.WITHDRAWN.value: [],
}


def _normalize_state(state: Union[str, IndentState, None]) -> str:
    if state is None:
        return ""
    if isinstance(state, IndentState):
        return state.value
    return str(state).strip().upper()


def can_transition(
    current_state: Union[str, IndentState],
    next_state: Union[str, IndentState],
) -> bool:
    """Validate whether transitioning from current_state to next_state is valid."""
    curr = _normalize_state(current_state)
    nxt = _normalize_state(next_state)
    allowed = TRANSITION_MATRIX.get(curr, [])
    return nxt in allowed


def is_modifiable(current_state: Union[str, IndentState]) -> bool:
    """Enforce BR-PSM-007: Indent is modifiable only in DRAFT and SUBMITTED states."""
    curr = _normalize_state(current_state)
    return curr in [IndentState.DRAFT.value, IndentState.SUBMITTED.value]
