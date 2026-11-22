"""Public contract for the LMS module. Plural getters only."""

from collections.abc import Sequence


def get_course_workspaces(course_ids: Sequence[int]) -> list[dict]:
    """Return course workspace DTOs for the given course ids."""
    return []


def get_materials(course_ids: Sequence[int]) -> list[dict]:
    """Return material DTOs for the given course ids."""
    return []
