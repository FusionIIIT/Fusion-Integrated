"""VMS capability catalogue consumed by the module registry publisher."""

MODULE = {
    "code": "vms",
    "label": "Visitor Management",
    "icon": "FaIdCard",
    "base_path": "/vms",
    "nav_section": "Visitor Management",
    "sort_order": 30,
    "status": "active",
}
NAV_ITEMS = [
    {
        "code": "vms.visits",
        "label": "Visitor requests",
        "icon": "FaUsers",
        "to": "/vms/visits",
        "required_permission": "vms.visit_request.view",
        "sort_order": 10,
    },
    {
        "code": "vms.inbox",
        "label": "Host approvals",
        "icon": "FaCheckDouble",
        "to": "/vms/inbox",
        "required_permission": "vms.visit_request.approve",
        "sort_order": 20,
    },
    {
        "code": "vms.admin_review",
        "label": "Urgent and contingency review",
        "icon": "FaClipboardCheck",
        "to": "/vms/admin-review",
        "required_permission": "vms.visit_request.approve",
        "sort_order": 25,
    },
    {
        "code": "vms.events",
        "label": "Special events",
        "icon": "FaCalendarAlt",
        "to": "/vms/admin/events",
        "required_permission": "vms.event.manage",
        "sort_order": 30,
    },
    {
        "code": "vms.security_events",
        "label": "Event operations",
        "icon": "FaCalendarAlt",
        "to": "/vms/security/events",
        "required_permission": "vms.event.view",
        "sort_order": 35,
    },
]
PERMISSIONS = [
    ("vms.visit_request.view", "View all visit requests"),
    ("vms.visit_request.view_self", "View visit requests for assigned host scope"),
    ("vms.visit_request.create", "Create and manage visit requests"),
    ("vms.visit_request.update", "Update or terminate visit requests"),
    ("vms.visit_request.approve", "Approve or reject visit requests"),
    ("vms.visit_request.expire", "Expire overdue requests"),
    ("vms.visit_log.create", "Record visit entry and exit events"),
    ("vms.gate.validate", "Validate visitor passes at gate checkpoints"),
    ("vms.gate.override", "Decide eligible manual gate overrides"),
    ("vms.document.view", "View cleared visitor identity documents"),
    ("vms.registry.manage", "Manage blacklist and safe-list versions"),
    ("vms.policy.manage", "Manage access policy versions"),
    ("vms.zone.manage", "Manage zone permissions and elevations"),
    ("vms.report.view", "View visitor reports and statistics"),
    ("vms.audit.view", "Review security audit events"),
    ("vms.event.view", "View special-event handling information"),
    ("vms.event.manage", "Manage special visitor events"),
    ("vms.muster.manage", "Manage emergency muster and roll call"),
    ("vms.integration.manage", "Manage VMS integration settings"),
    ("vms.vip.manage", "Manage VIP permissions"),
    ("vms.role.manage", "Assign scoped VMS roles"),
]
SYSTEM_PERMISSIONS = ["vms.visit_request.expire"]
ALL_ADMIN = [code for code, _ in PERMISSIONS if code not in SYSTEM_PERMISSIONS]
SECURITY = [
    "vms.visit_request.view",
    "vms.visit_log.create",
    "vms.gate.validate",
    "vms.document.view",
    "vms.event.view",
    "vms.report.view",
    "vms.muster.manage",
]
HOST = [
    "vms.visit_request.view_self",
    "vms.visit_request.approve",
    "vms.visit_request.create",
    "vms.visit_request.update",
    "vms.visit_log.create",
]
ROLE_GRANTS = {
    "Super Admin": ALL_ADMIN,
    "Admin": [p for p in ALL_ADMIN if p != "vms.role.manage"],
    "Security Personnel": SECURITY,
    "faculty": HOST,
    "staff": HOST,
}
MODULE_GRANTS = list(ROLE_GRANTS)
