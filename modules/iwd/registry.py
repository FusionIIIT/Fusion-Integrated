# modules/iwd/registry.py
"""
Fusion-Integrated module registry for the IWD V2 system.

This file follows the same structure as the placement module registry
(`modules/placement/registry.py`).  It defines the module metadata, navigation
items, permissions, and role grants for the IWD V2 role concepts.
"""

# --------------------------------------------------------------------------- #
# MODULE
# --------------------------------------------------------------------------- #
MODULE = {
    "code": "iwd",
    "label": "Integrated Work Delivery",
    "icon": "iwd",
    "base_path": "/iwd",
    "nav_section": "iwd",
    "sort_order": 30,
    "status": "active",
}

# --------------------------------------------------------------------------- #
# NAVIGATION ITEMS
# --------------------------------------------------------------------------- #
NAV_ITEMS = [
    {
        "code": "iwd.requests",
        "label": "Requests",
        "icon": "iwd",
        "to": "/iwd/requests",
        "required_permission": "iwd.request.view_self",
        "sort_order": 10,
    },
    # Additional navigation items can be added here when routes are implemented.
]

# --------------------------------------------------------------------------- #
# PERMISSIONS
# --------------------------------------------------------------------------- #
PERMISSIONS = [
    ("iwd.request.create", "Create a new IWD request"),
    ("iwd.request.view_self", "View own IWD requests"),
    ("iwd.request.view_all", "View all IWD requests"),
    ("iwd.request.admin_approve", "Admin IWD first approval of requests"),
    ("iwd.request.hod_approve", "HOD/Dean second approval of requests"),
    ("iwd.request.director_approve", "Director final approval of requests"),
    ("iwd.proposal.manage", "Create and manage proposals"),
    ("iwd.work_order.issue", "Issue work orders"),
    ("iwd.work.update", "Update and complete work orders"),
    ("iwd.bill.view", "View bills"),
    ("iwd.bill.manage", "Manage bills"),
    ("iwd.bill.audit", "Audit bills"),
    ("iwd.bill.settle", "Settle bills"),
    ("iwd.inventory.manage", "Manage inventory and operations"),
    ("iwd.feedback.submit", "Submit feedback"),
    ("iwd.sla.view", "View SLA metrics"),
]

# --------------------------------------------------------------------------- #
# ROLE GRANTS
# --------------------------------------------------------------------------- #
ROLE_GRANTS = {
    # Request Initiator (Engineer/HOD/Dean)
    "Request Initiator": [
        "iwd.request.create",
        "iwd.request.view_self",
    ],

    # Admin IWD
    "Admin IWD": [
        "iwd.request.admin_approve",
        "iwd.proposal.manage",
        "iwd.work_order.issue",
        "iwd.inventory.manage",
        "iwd.request.view_all",
    ],

    # HOD/Dean
    "HOD/Dean": [
        "iwd.request.hod_approve",
    ],

    # Director
    "Director": [
        "iwd.request.director_approve",
    ],

    # Engineer
    "Engineer": [
        "iwd.proposal.manage",
        "iwd.work.update",
    ],

    # Auditor
    "Auditor": [
        "iwd.bill.audit",
    ],

    # Accounts Admin
    "Accounts Admin": [
        "iwd.bill.manage",
        "iwd.bill.settle",
    ],

    # Authenticated users (any logged‑in user)
    "Authenticated": [
        "iwd.feedback.submit",
        "iwd.sla.view",
        "iwd.bill.view",
    ],
}

