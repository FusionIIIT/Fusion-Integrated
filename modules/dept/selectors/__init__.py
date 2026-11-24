"""Selectors for Department module."""

from modules.dept.selectors.announcements import list_announcements_for_principal
from modules.dept.selectors.department import (
    get_department_with_headship,
    list_pending_official_changes,
)
from modules.dept.selectors.feedback import list_feedback_for_principal
from modules.dept.selectors.inventory import (
    list_inventory_items,
    list_stock_requests_for_principal,
    list_stock_transactions,
)
from modules.dept.selectors.labs import list_lab_resources, list_role_assignments
from modules.dept.selectors.profiles import list_profiles, mask_profile_for_viewer
from modules.dept.selectors.scoping import assert_department_access, resolve_department_code
from modules.dept.selectors.timetable import get_existing_slots, list_timetables

__all__ = [
    "assert_department_access",
    "get_department_with_headship",
    "get_existing_slots",
    "list_announcements_for_principal",
    "list_feedback_for_principal",
    "list_inventory_items",
    "list_lab_resources",
    "list_pending_official_changes",
    "list_profiles",
    "list_role_assignments",
    "list_stock_requests_for_principal",
    "list_stock_transactions",
    "list_timetables",
    "mask_profile_for_viewer",
    "resolve_department_code",
]
