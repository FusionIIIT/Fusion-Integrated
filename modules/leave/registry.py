"""Leave Management module registry.

Defines MODULE and NAV_ITEMS with permission-based navigation.
Follows placement module pattern.
"""
from __future__ import annotations

from fusion_auth.permissions import HasModuleGrant

# Module code - must match the module name
MODULE = HasModuleGrant("leave_management")

# Permission codes for leave operations
P_VIEW_LEAVE = "leave_management.leave.view"
P_VIEW_LEAVE_BALANCE = "leave_management.leave.balance.view"
P_CREATE_LEAVE = "leave_management.leave.create"
P_APPROVE_LEAVE = "leave_management.leave.approve"
P_CANCEL_LEAVE = "leave_management.leave.cancel"
P_VIEW_SANCTIONS = "leave_management.leave.sanction.view"
P_VIEW_POLICIES = "leave_management.leave.policy.view"
P_MANAGE_POLICIES = "leave_management.leave.policy.manage"
P_VIEW_HOLIDAY_CALENDAR = "leave_management.leave.holiday.view"


def _get_nav_items_for_role(permissions: frozenset) -> list[dict]:
    """Filter navigation items based on user permissions."""
    # Define navigation items for the leave module
    nav_items = [
        {
            "code": "leave_requests",
            "label": "Leave Requests",
            "icon": "FaCalendar",
            "to": "/leave/requests/",
            "required_permission": P_VIEW_LEAVE,
        },
        {
            "code": "my_leave",
            "label": "My Leave Balance",
            "icon": "FaUserClock",
            "to": "/leave/balance/",
            "required_permission": P_VIEW_LEAVE_BALANCE,
        },
        {
            "code": "leave_policy",
            "label": "Leave Policy",
            "icon": "FaFileContract",
            "to": "/leave/policy/",
            "required_permission": P_VIEW_POLICIES,
        },
        {
            "code": "holiday_calendar",
            "label": "Holiday Calendar",
            "icon": "FaCalendarAlt",
            "to": "/leave/holiday/",
            "required_permission": P_VIEW_HOLIDAY_CALENDAR,
        },
        {
            "code": "sanctions",
            "label": "Sanctions",
            "icon": "FaGavel",
            "to": "/leave/sanctions/",
            "required_permission": P_VIEW_SANCTIONS,
        },
    ]

    # Filter items based on permissions
    filtered_items = []
    for item in nav_items:
        if item["required_permission"]:
            # Check if user has the required permission
            if item["required_permission"] in permissions:
                filtered_items.append(item)
        else:
            # No permission required, include by default
            filtered_items.append(item)

    return filtered_items


def get_nav_items() -> list[dict]:
    """Get navigation items filtered by user's permissions."""
    # In production, this would read from request.principal.permissions
    # For now, return all items
    return _get_nav_items_for_role(frozenset())
