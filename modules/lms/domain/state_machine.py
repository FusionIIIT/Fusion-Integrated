"""Declarative state machines for LMS workflows (CW-LMS-01, CW-LMS-02, BW-LMS-01).

Pure Python — no Django imports.
"""
from dataclasses import dataclass

from .entities import AssignmentStatus, GradeStatus, MaterialStatus
from .errors import InvalidTransition


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    description: str = ""


# CW-LMS-01 & BW-LMS-02 / BW-LMS-03: Assignment Publication Lifecycle
ASSIGNMENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(AssignmentStatus.DRAFT.value, AssignmentStatus.AVAILABLE.value, "Immediate assignment publication"),
    Transition(AssignmentStatus.DRAFT.value, AssignmentStatus.SCHEDULED.value, "Schedule assignment for future release"),
    Transition(AssignmentStatus.SCHEDULED.value, AssignmentStatus.AVAILABLE.value, "Scheduled release time reached; assignment open"),
)

# BW-LMS-01: Material Publication Lifecycle
MATERIAL_TRANSITIONS: tuple[Transition, ...] = (
    Transition(MaterialStatus.DRAFT.value, MaterialStatus.PUBLISHED.value, "Immediate material publication"),
    Transition(MaterialStatus.DRAFT.value, MaterialStatus.SCHEDULED.value, "Schedule material for future release"),
    Transition(MaterialStatus.SCHEDULED.value, MaterialStatus.PUBLISHED.value, "Scheduled release time reached; material published"),
)

# CW-LMS-02 & BW-LMS-04 / BW-LMS-05: Grading and Grade Release Lifecycle
GRADE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(GradeStatus.DRAFT.value, GradeStatus.RELEASED.value, "Faculty releases grade to student"),
)


def validate_assignment_transition(from_status: str, to_status: str) -> None:
    """Validate assignment workflow transition (CW-LMS-01)."""
    for t in ASSIGNMENT_TRANSITIONS:
        if t.frm == from_status and t.to == to_status:
            return
    raise InvalidTransition(f"Illegal assignment transition from '{from_status}' to '{to_status}'.")


def validate_material_transition(from_status: str, to_status: str) -> None:
    """Validate material workflow transition (BW-LMS-01)."""
    for t in MATERIAL_TRANSITIONS:
        if t.frm == from_status and t.to == to_status:
            return
    raise InvalidTransition(f"Illegal material transition from '{from_status}' to '{to_status}'.")


def validate_grade_transition(from_status: str, to_status: str) -> None:
    """Validate grading workflow transition (CW-LMS-02)."""
    for t in GRADE_TRANSITIONS:
        if t.frm == from_status and t.to == to_status:
            return
    raise InvalidTransition(f"Illegal grade transition from '{from_status}' to '{to_status}'.")
