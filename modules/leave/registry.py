"""Leave Management (ELM) module.

What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave", "label": "Leave Management", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "Check", "to": "/leave/apply", "required_permission": "leave.registration.self", "sort_order": 5},
    {"code": "leave.mine", "label": "My Leave", "icon": "User", "to": "/leave/mine", "required_permission": "leave.application.view_self", "sort_order": 10},
    {"code": "leave.approvals", "label": "Leave Approvals", "icon": "Check", "to": "/leave/approvals", "required_permission": "leave.registration.manage", "sort_order": 15},
    {"code": "leave.substitute", "label": "Leave Substitute", "icon": "User", "to": "/leave/substitute", "required_permission": "leave.substitute.accept", "sort_order": 20},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "leave.interview", "label": "Interview", "icon": "Calendar", "to": "/leave/interview", "required_permission": "leave.interview.schedule", "sort_order": 25},
    {"code": "leave.offer", "label": "Offer", "icon": "Envelope", "to": "/leave/offer", "required_permission": "leave.offer.respond", "sort_order": 30},
    {"code": "leave.cancel", "label": "Cancel Leave", "icon": "Cancel", "to": "/leave/cancel", "required_permission": "leave.cancel.leave", "sort_order": 35},

    # -- leave administrator -------------------------------------------
    {"code": "leave.admin", "label": "Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave.admin.manage", "sort_order": 40},
]

PERMISSIONS = [
    ("leave.registration.self", "Register for leave"),
    ("leave.interview.schedule", "Schedule leave interview"),
    ("leave.offer.respond", "Respond to leave offer"),
    ("leave.cancel.leave", "Cancel leave request"),
    ("leave.admin.manage", "Manage leave records"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "employee": ["leave.registration.self", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "unit_head": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "deputy_registrar": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "dean": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "registrar": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "director": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "leave_admin": ["leave.admin.manage"],
}

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "employee": ["leave.registration.self", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "unit_head": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "deputy_registrar": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "dean": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "registrar": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "director": ["leave.registration.manage", "leave.interview.schedule", "leave.offer.respond", "leave.cancel.leave"],
    "leave_admin": ["leave.admin.manage"],
}
