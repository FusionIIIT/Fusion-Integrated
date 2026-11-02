"""Lifecycle values directly represented in the LMS specifications."""

MATERIAL_DRAFT = "draft"
MATERIAL_SCHEDULED = "scheduled"
MATERIAL_PUBLISHED = "published"

ASSIGNMENT_DRAFT = "draft"
ASSIGNMENT_SCHEDULED = "scheduled"
ASSIGNMENT_AVAILABLE = "available"

GRADE_DRAFT = "draft"
GRADE_RELEASED = "released"


def material_state(*, release_at, now):
    return MATERIAL_SCHEDULED if release_at and release_at > now else MATERIAL_PUBLISHED


def assignment_state(*, release_at, now):
    return ASSIGNMENT_SCHEDULED if release_at and release_at > now else ASSIGNMENT_AVAILABLE
