"""What the server tells the shell about this module (ADR-0010).

Nav items carry ``required_permission`` and the server filters before sending --
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "Leave Management",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee views -------------------------------------------------------
    {"code": "elm.apply", "label": "Apply for Leave",
     "icon": "FaFileSignature", "to": "/elm/apply",
     "required_permission": "elm.leave.apply", "sort_order": 10},
    {"code": "elm.my_leaves", "label": "My Leaves",
     "icon": "FaCalendarAlt", "to": "/elm/my-leaves",
     "required_permission": "elm.leave.view_self", "sort_order": 20},
    {"code": "elm.my_balance", "label": "Leave Balance",
     "icon": "FaChartBar", "to": "/elm/balance",
     "required_permission": "elm.leave.view_self", "sort_order": 30},

    # -- Substitute view ------------------------------------------------------
    {"code": "elm.substitute", "label": "Substitute Requests",
     "icon": "FaUserCheck", "to": "/elm/substitute",
     "required_permission": "elm.leave.respond_substitute", "sort_order": 40},

    # -- Approval views (Unit Head / Sanctioning Authority) --------------------
    {"code": "elm.pending", "label": "Pending Approvals",
     "icon": "FaClipboardCheck", "to": "/elm/pending",
     "required_permission": "elm.leave.approve", "sort_order": 50},
    {"code": "elm.all_leaves", "label": "All Leaves",
     "icon": "FaUsers", "to": "/elm/all-leaves",
     "required_permission": "elm.leave.view_all", "sort_order": 60},

    # -- Admin views -----------------------------------------------------------
    {"code": "elm.calendar", "label": "Holiday Calendar",
     "icon": "FaCalendarAlt", "to": "/elm/calendar",
     "required_permission": "elm.admin.manage_calendar", "sort_order": 80},
    {"code": "elm.offline", "label": "Record Offline Leave",
     "icon": "FaClipboardList", "to": "/elm/offline",
     "required_permission": "elm.admin.record_offline", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    # Employee actions
    ("elm.leave.apply", "Submit a leave request"),
    ("elm.leave.view_self", "View own leave history and balance"),
    ("elm.leave.cancel", "Withdraw pending or cancel approved leave"),
    ("elm.leave.modify", "Request extension or submit resumption"),
    ("elm.leave.respond_substitute", "Accept or decline substitute nomination"),

    # Approval actions (BR-EL-016, BR-EL-017, BR-EL-018)
    ("elm.leave.approve", "Approve, reject, or recommend a leave request"),
    ("elm.leave.view_all", "View all employees' leave data"),
    ("elm.leave.report", "Generate leave balance and year-end reports"),

    # Admin actions (BR-EL-029, BR-EL-031, BR-EL-037, BR-EL-038)
    ("elm.admin.manage_calendar", "Publish and edit holiday/RH calendar"),
    ("elm.admin.record_offline", "Record offline-sanctioned leave"),
    ("elm.admin.year_end", "Run year-end balance processing"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.admin.year_end",
]

#: Enforced by widening selectors rather than hard 403 on an endpoint.
SCOPE_PERMISSIONS = [
    "elm.leave.view_all",
]

# Role -> permission sets (BR-EL-036)
_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.cancel",
    "elm.leave.modify",
    "elm.leave.respond_substitute",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "elm.leave.approve",
    "elm.leave.view_all",
    "elm.leave.report",
]

_SANCTION_AUTHORITY = [
    *_UNIT_HEAD,
]

_ESTABLISHMENT = [
    "elm.leave.approve",
    "elm.leave.view_all",
]

_ADMIN = [
    *_SANCTION_AUTHORITY,
    "elm.admin.manage_calendar",
    "elm.admin.record_offline",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "establishment": _ESTABLISHMENT,
    "sanction_authority": _SANCTION_AUTHORITY,
    "elm_admin": _ADMIN,
}
