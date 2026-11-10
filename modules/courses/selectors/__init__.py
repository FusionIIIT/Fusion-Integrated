"""Selectors package for courses module."""
from .announcements import get_announcement_for_actor, visible_announcements
from .assignments import get_assignment_for_actor, visible_assignments
from .materials import (
    get_material_for_actor,
    get_section_for_actor,
    visible_materials,
    visible_sections,
)
from .scoping import (
    get_workspace_membership,
    get_workspace_personnel_ids,
    is_course_instructor,
    visible_workspaces,
)

__all__ = [
    "get_announcement_for_actor",
    "get_assignment_for_actor",
    "get_material_for_actor",
    "get_section_for_actor",
    "get_workspace_membership",
    "get_workspace_personnel_ids",
    "is_course_instructor",
    "visible_announcements",
    "visible_assignments",
    "visible_materials",
    "visible_sections",
    "visible_workspaces",
]
