"""What the server tells the shell about VMS, and every permission it knows.

Nav items carry `required_permission` and the server filters before sending,
so a link a role cannot use never reaches the browser.

Ref: 03_VMS_Use_Case_Specifications_v1.3 (actors and role matrix)
"""
MODULE = {
    "code": "visitors", "label": "Visitors", "icon": "UserCheck",
    "base_path": "/visitors", "nav_section": "Visitors", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "visitors.register", "label": "Register Visit",
     "icon": "FilePlus", "to": "/visitors/register",
     "required_permission": "visitors.visit.register", "sort_order": 10},
    {"code": "visitors.mine", "label": "My Visits",
     "icon": "CalendarCheck", "to": "/visitors/mine",
     "required_permission": "visitors.visit.view_self", "sort_order": 20},
    {"code": "visitors.host_pending", "label": "Pending Approvals",
     "icon": "ClipboardText", "to": "/visitors/host/pending",
     "required_permission": "visitors.visit.host_decide", "sort_order": 30},
    {"code": "visitors.host_arrivals", "label": "Visitor Arrivals",
     "icon": "UserCheck", "to": "/visitors/host/arrivals",
     "required_permission": "visitors.visit.host_view", "sort_order": 40},
    {"code": "visitors.gate_dashboard", "label": "Gate Dashboard",
     "icon": "Shield", "to": "/visitors/gate/dashboard",
     "required_permission": "visitors.gate.operate", "sort_order": 50},
    {"code": "visitors.walkin", "label": "Walk-in Registration",
     "icon": "DoorOpen", "to": "/visitors/gate/walkin",
     "required_permission": "visitors.gate.operate", "sort_order": 60},
    {"code": "visitors.admin_pending", "label": "Admin Queue",
     "icon": "Stamp", "to": "/visitors/admin/pending",
     "required_permission": "visitors.admin.decide", "sort_order": 70},
    {"code": "visitors.reports", "label": "Reports & Analytics",
     "icon": "ChartBar", "to": "/visitors/admin/reports",
     "required_permission": "visitors.admin.report", "sort_order": 80},
    {"code": "visitors.blacklist", "label": "Blacklist Registry",
     "icon": "ShieldWarning", "to": "/visitors/admin/blacklist",
     "required_permission": "visitors.blacklist.manage", "sort_order": 90},
    {"code": "visitors.zones", "label": "Zone Management",
     "icon": "MapPin", "to": "/visitors/zones",
     "required_permission": "visitors.zone.validate", "sort_order": 100},
    {"code": "visitors.policies", "label": "Access Policies",
     "icon": "GearSix", "to": "/visitors/admin/policies",
     "required_permission": "visitors.policy.manage", "sort_order": 110},
    {"code": "visitors.muster", "label": "Emergency Muster",
     "icon": "Siren", "to": "/visitors/muster",
     "required_permission": "visitors.muster.trigger", "sort_order": 120},
]

PERMISSIONS = [
    ("visitors.visit.register", "Pre-register a visit"),
    ("visitors.visit.view_self", "View own visit requests and history"),
    ("visitors.visit.host_decide", "Approve or reject visit requests as host"),
    ("visitors.visit.host_view", "View visitor arrivals as host"),
    ("visitors.visit.terminate", "Terminate a visit early"),
    ("visitors.gate.operate",
     "Gate operations: walk-in registration, pass validation, checkout"),
    ("visitors.gate.override", "Process manual gate override"),
    ("visitors.zone.validate", "Validate zone access at checkpoints"),
    ("visitors.zone.elevate", "Grant temporary zone elevation"),
    ("visitors.admin.decide",
     "Admin decisions: contingency, extension, urgent approvals"),
    ("visitors.admin.report", "Generate visitor reports and analytics"),
    ("visitors.blacklist.manage", "Manage blacklist, watchlist, and safe-list"),
    ("visitors.muster.trigger", "Trigger emergency muster"),
    ("visitors.muster.roll_call", "Perform emergency roll-call"),
    ("visitors.policy.manage", "Manage access policies and VMS configuration"),
    ("visitors.role.assign", "Assign VMS roles (Super Admin only)"),
]

SYSTEM_PERMISSIONS = []

_VISITOR = [
    "visitors.visit.register",
    "visitors.visit.view_self",
]

_HOST = [
    *_VISITOR,
    "visitors.visit.host_decide",
    "visitors.visit.host_view",
    "visitors.visit.terminate",
]

_SECURITY = [
    "visitors.visit.view_self",
    "visitors.gate.operate",
    "visitors.zone.validate",
    "visitors.muster.roll_call",
]

_ADMIN = [
    *_HOST,
    *_SECURITY,
    "visitors.gate.override",
    "visitors.zone.elevate",
    "visitors.admin.decide",
    "visitors.admin.report",
    "visitors.blacklist.manage",
    "visitors.muster.trigger",
    "visitors.policy.manage",
    "visitors.visit.terminate",
]

_SUPER_ADMIN = [
    *_ADMIN,
    "visitors.role.assign",
]

ROLE_GRANTS = {
    "student": _VISITOR,
    "faculty": _HOST,
    "staff": _HOST,
    "Security Personnel": _SECURITY,
    "Admin": _ADMIN,
    "Super Admin": _SUPER_ADMIN,
}
