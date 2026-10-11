MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Leave Management",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # Student roles
    {"code": "elm.leave.apply", "label": "Apply for Leave", "icon": "File", "to": "/elm/apply", "required_permission": "elm.leave.apply", "sort_order": 10},
    {"code": "elm.leave.view_self", "label": "View My Leave Applications", "icon": "Eye", "to": "/elm/view_self", "required_permission": "elm.leave.view_self", "sort_order": 20},
    {"code": "elm.leave.withdraw", "label": "Withdraw Leave Application", "icon": "X", "to": "/elm/withdraw", "required_permission": "elm.leave.withdraw", "sort_order": 30},

    # Coordinator roles
    {"code": "elm.leave.review", "label": "Review Leave Applications", "icon": "FileCheck", "to": "/elm/review", "required_permission": "elm.leave.review", "sort_order": 40},

    # Officer roles
    {"code": "elm.leave.respond", "label": "Respond to Leave Application", "icon": "FileCheck", "to": "/elm/respond", "required_permission": "elm.leave.respond", "sort_order": 50},
    {"code": "elm.leave.sanction", "label": "Sanction Leave Application", "icon": "FileCheck", "to": "/elm/sanction", "required_permission": "elm.leave.sanction", "sort_order": 60},
    {"code": "elm.leave.cancel", "label": "Cancel Leave Application", "icon": "FileX", "to": "/elm/cancel", "required_permission": "elm.leave.cancel", "sort_order": 70},
    {"code": "elm.leave.extend", "label": "Extend Leave Application", "icon": "FilePlus", "to": "/elm/extend", "required_permission": "elm.leave.extend", "sort_order": 80},
    {"code": "elm.leave.resume", "label": "Resume Leave", "icon": "FilePlay", "to": "/elm/resume", "required_permission": "elm.leave.resume", "sort_order": 90},

    # Leave Administrator roles
    {"code": "elm.leave.admin", "label": "Administrative Actions", "icon": "Gear", "to": "/elm/admin", "required_permission": "elm.leave.admin", "sort_order": 100},
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view_self", "View own leave applications"),
    ("elm.leave.withdraw", "Withdraw own leave applications"),
    ("elm.leave.review", "Review leave applications"),
    ("elm.leave.respond", "Respond to leave applications"),
    ("elm.leave.sanction", "Sanction leave applications"),
    ("elm.leave.cancel", "Cancel leave applications"),
    ("elm.leave.extend", "Extend leave applications"),
    ("elm.leave.resume", "Resume leave applications"),
    ("elm.leave.admin", "Perform administrative actions related to leave management"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.respond",
    "elm.leave.review",
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.leave.admin",
]

_STUDENT = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.respond",
]

_COORDINATOR = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.respond",
    "elm.leave.review",
]

_OFFICER = [
    *_COORDINATOR,
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.leave.admin",
]

_LEAVE_ADMIN = [
    *_OFFICER,
    "elm.leave.admin",
]

ROLE_GRANTS = {
    "faculty": _STUDENT,
    "staff": _STUDENT,
    "Unit Head": _COORDINATOR,
    "Deputy Registrar (Estt.)": _OFFICER,
    "Dean": _OFFICER,
    "Registrar": _OFFICER,
    "Director": _OFFICER,
    "Leave Administrator": _LEAVE_ADMIN,
}
