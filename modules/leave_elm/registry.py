"""Module registry configuration for Employee Leave Management.
    
Contains MODULE metadata, NAV_ITEMS for navigation, PERMISSIONS, and ROLE_GRANTS
for RBAC (Role-Based Access Control) integration with Fusion authentication system.
"""

from typing import Tuple, Dict, List

# Module metadata - NOTE: Uses 'code' instead of 'name'/slug as per platform requirements
MODULE = {
    "code": "leave_elm",
    "name": "Employee Leave Management",
    "slug": "leave_elm",
    # admin-only module without client routes; base_path empty means no prefix check for nav
    "base_path": "",
    "description": "Manage employee leave entitlements, applications, approvals, and substitute coverage.",
}

# Navigation items for the admin frontend - list of dicts with required keys
NAV_ITEMS: List[Dict[str, str]] = [
    {"code": "leave_elm", "label": "Leaves", "icon": "leaves", "to": "/admin/leave_elm/", "required_permission": "leave_elm.application.view", "sort_order": 1},
]

# Permission definitions: permission code -> description
PERMISSIONS: List[Tuple[str, str]] = (
    # Leave Balance Permissions
    ("leave_elm.balance.view", "View personal leave balances"),
    
    # Leave Application Permissions
    ("leave_elm.application.view_self", "View own leave applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.cancel", "Cancel own leave application"),
    ("leave_elm.application.view", "View leave applications (all)"),
    
    # Application State Management Permissions
    ("leave_elm.application.recommend", "Recommend leave approval"),
    ("leave_elm.application.approve", "Approve leave request"),
    ("leave_elm.application.reject", "Reject leave request"),
    
    # Substitute Coverage Permissions
    ("leave_elm.substitute.view_self", "View own substitute responses"),
    ("leave_elm.substitute.respond", "Respond to substitute request"),
    ("leave_elm.substitute.approve", "Approve substitute coverage"),
    ("leave_elm.substitute.decline", "Decline substitute coverage"),
    
    # Reporting and Analytics Permissions
    ("leave_elm.report.view", "View leave reports"),
    ("leave_elm.bulk.action", "Perform bulk leave actions"),
)

# Role grants mapping: role name -> list of permission code strings (plain strings, no tuples)
ROLE_GRANTS: Dict[str, List[str]] = {
    "Employee": [
        "leave_elm.balance.view",
        "leave_elm.application.view_self",
        "leave_elm.application.apply",
        "leave_elm.application.cancel",
        "leave_elm.substitute.view_self",
        "leave_elm.substitute.respond",
        "leave_elm.substitute.approve",
        "leave_elm.substitute.decline",
        "leave_elm.report.view",
    ],
    
    "Leave Approver": [
        "leave_elm.balance.view",
        "leave_elm.application.view_self",
        "leave_elm.application.apply",
        "leave_elm.application.cancel",
        "leave_elm.application.view",
        "leave_elm.substitute.view_self",
        "leave_elm.substitute.respond",
        "leave_elm.application.recommend",
        "leave_elm.report.view",
    ],
    
    "HOD": [  # Head of Department / Unit Head
        "leave_elm.balance.view",
        "leave_elm.application.view_self",
        "leave_elm.application.apply",
        "leave_elm.application.cancel",
        "leave_elm.application.view",
        "leave_elm.substitute.view_self",
        "leave_elm.substitute.respond",
        "leave_elm.application.recommend",
        "leave_elm.application.approve",
        "leave_elm.application.reject",
        "leave_elm.report.view",
    ],
    
    "Registrar": [  # Higher authority for final sanctioning
        "leave_elm.balance.view",
        "leave_elm.application.view_self",
        "leave_elm.application.apply",
        "leave_elm.application.cancel",
        "leave_elm.application.view",
        "leave_elm.substitute.view_self",
        "leave_elm.substitute.respond",
        "leave_elm.application.recommend",
        "leave_elm.application.approve",
        "leave_elm.application.reject",
        "leave_elm.bulk.action",
        "leave_elm.report.view",
    ],
}


def get_module_info() -> Dict:
    """Get module metadata for registry purposes."""
    return MODULE


def get_permissions() -> Tuple[Tuple[str, str], ...]:
    """Get all registered permissions."""
    return PERMISSIONS


def get_role_grants() -> Dict[str, List[str]]:
    """Get role-to-permission mappings."""
    return ROLE_GRANTS