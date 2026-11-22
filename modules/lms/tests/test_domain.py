"""Domain tests: pure Python, no database, milliseconds."""

from modules.lms.domain.state_machine import (
    ASSIGNMENT_TRANSITIONS,
    GRADE_TRANSITIONS,
    MATERIAL_TRANSITIONS,
    AssignmentStatus,
    GradeStatus,
    MaterialStatus,
    transition,
)


def test_material_transitions():
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.DRAFT, "publish") == MaterialStatus.PUBLISHED
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.DRAFT, "schedule") == MaterialStatus.SCHEDULED
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.SCHEDULED, "release") == MaterialStatus.PUBLISHED
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.PUBLISHED, "publish") is None
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.SCHEDULED, "publish") is None


def test_assignment_transitions():
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.DRAFT, "publish_immediate") == AssignmentStatus.AVAILABLE
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.DRAFT, "publish_scheduled") == AssignmentStatus.SCHEDULED
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.SCHEDULED, "release") == AssignmentStatus.AVAILABLE
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.AVAILABLE, "publish_immediate") is None
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.DRAFT, "release") is None


def test_grade_transitions():
    assert transition(GRADE_TRANSITIONS, GradeStatus.DRAFT, "release") == GradeStatus.RELEASED
    assert transition(GRADE_TRANSITIONS, GradeStatus.RELEASED, "release") is None


def test_illegal_transitions_return_none():
    # Published material can't be scheduled
    assert transition(MATERIAL_TRANSITIONS, MaterialStatus.PUBLISHED, "schedule") is None
    # Released grade can't be re-released
    assert transition(GRADE_TRANSITIONS, GradeStatus.RELEASED, "release") is None
    # Available assignment can't be re-published
    assert transition(ASSIGNMENT_TRANSITIONS, AssignmentStatus.AVAILABLE, "publish_immediate") is None
