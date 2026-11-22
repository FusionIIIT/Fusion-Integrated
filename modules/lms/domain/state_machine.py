"""Domain logic: state machines, pure Python, no Django/DRF/Celery."""

from enum import StrEnum


class MaterialStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"


class AssignmentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    AVAILABLE = "available"


class SubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"


class GradeStatus(StrEnum):
    DRAFT = "draft"
    RELEASED = "released"


# --- Material transitions ---
MATERIAL_TRANSITIONS = {
    (MaterialStatus.DRAFT, "publish"): MaterialStatus.PUBLISHED,
    (MaterialStatus.DRAFT, "schedule"): MaterialStatus.SCHEDULED,
    (MaterialStatus.SCHEDULED, "release"): MaterialStatus.PUBLISHED,
}

# --- Assignment transitions ---
ASSIGNMENT_TRANSITIONS = {
    (AssignmentStatus.DRAFT, "publish_immediate"): AssignmentStatus.AVAILABLE,
    (AssignmentStatus.DRAFT, "publish_scheduled"): AssignmentStatus.SCHEDULED,
    (AssignmentStatus.SCHEDULED, "release"): AssignmentStatus.AVAILABLE,
}

# --- Grade transitions ---
GRADE_TRANSITIONS = {
    (GradeStatus.DRAFT, "release"): GradeStatus.RELEASED,
}


def transition(table, current, event):
    """Return the new state, or None if the transition is illegal."""
    return table.get((current, event))
