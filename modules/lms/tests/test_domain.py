"""Domain unit tests for LMS state machines and transitions.

Zero database and zero Django dependencies.
"""
import pytest

from modules.lms.domain.entities import AssignmentStatus, GradeStatus, MaterialStatus
from modules.lms.domain.errors import InvalidTransition
from modules.lms.domain.state_machine import (
    validate_assignment_transition,
    validate_grade_transition,
    validate_material_transition,
)


def test_assignment_draft_can_transition_to_available():
    """BW-LMS-02: Immediate publication."""
    validate_assignment_transition("draft", "available")


def test_assignment_draft_can_transition_to_scheduled():
    """BW-LMS-03: Scheduled publication."""
    validate_assignment_transition("draft", "scheduled")


def test_assignment_scheduled_can_transition_to_available():
    """BW-LMS-03: Scheduled release time reached."""
    validate_assignment_transition("scheduled", "available")


def test_illegal_assignment_transition_raises():
    """Cannot jump from available back to draft."""
    with pytest.raises(InvalidTransition):
        validate_assignment_transition("available", "draft")


def test_material_draft_can_transition_to_published():
    """Immediate material publish."""
    validate_material_transition("draft", "published")


def test_material_draft_can_transition_to_scheduled():
    """Scheduled material publish."""
    validate_material_transition("draft", "scheduled")


def test_illegal_material_transition_raises():
    with pytest.raises(InvalidTransition):
        validate_material_transition("published", "draft")


def test_grade_draft_can_transition_to_released():
    """BW-LMS-04: Grade draft to released."""
    validate_grade_transition("draft", "released")


def test_illegal_grade_transition_raises():
    with pytest.raises(InvalidTransition):
        validate_grade_transition("released", "draft")
