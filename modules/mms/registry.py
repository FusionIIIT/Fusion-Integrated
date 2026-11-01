"""MMS module registry — nav and permission declarations.

Roles defined by the MMS spec (v1.4 FINAL):
  - mess_admin: assigns operational roles, cannot touch operational data
  - mess_caretaker: manages registration requests, menus, bills
  - mess_warden: oversight and escalation
  - student: submits registration/deregistration requests, views own data
"""

MODULE = {
    "code": "mms",
    "label": "Mess Management",
    "icon": "FaUtensils",
    "base_path": "/mms",
    "nav_section": "Campus",
    "sort_order": 200,
    "status": "planned",  # flip to "active" in the final commit
}

NAV_ITEMS = [
    # Student nav
    {
        "code": "mms.my-registration",
        "label": "My Registration",
        "icon": "FaClipboardList",
        "to": "/mms/my-registration",
        "required_permission": "mms.registration.view_self",
        "sort_order": 10,
    },
    # Caretaker nav
    {
        "code": "mms.registrations",
        "label": "Registration Requests",
        "icon": "FaInbox",
        "to": "/mms/registrations",
        "required_permission": "mms.registration.review",
        "sort_order": 20,
    },
    # Warden nav — oversight
    {
        "code": "mms.overview",
        "label": "Overview",
        "icon": "FaChartBar",
        "to": "/mms/overview",
        "required_permission": "mms.registration.view",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("mms.registration.view_self", "View own mess registration and history"),
    ("mms.registration.create", "Submit a mess registration request"),
    ("mms.registration.view", "View all registration requests (warden scope)"),
    ("mms.registration.review", "Approve or reject registration requests"),
]

SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = [
    "mms.registration.view_self",
    "mms.registration.create",
]

_CARETAKER = [
    "mms.registration.view",
    "mms.registration.review",
]

_WARDEN = [
    "mms.registration.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "mess_caretaker": _CARETAKER,
    "mess_warden": _WARDEN,
}
