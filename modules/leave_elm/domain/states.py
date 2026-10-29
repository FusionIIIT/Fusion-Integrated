"""States for the substitute decline/acceptance leave workflow."""

from enum import Enum


class LeaveWorkflowState(str, Enum):
    """A leave workflow's relevant states."""

    APPROVED = "APPROVED"
    SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED"
    SUBSTITUTE_ACCEPTED = "SUBSTITUTE_ACCEPTED"
    END = "END"
