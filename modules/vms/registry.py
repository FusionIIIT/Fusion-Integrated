"""What the server tells the shell about this module (ADR-0010).

The sidebar items are declared here once the client screens exist; until
then `NAV_ITEMS` is empty, which is exactly what nav_matches_routes wants —
a link with no route is worse than no link.
"""
MODULE = {
    "code": "vms", "label": "Visitor Management", "icon": "UserCheck",
    "base_path": "/vms", "nav_section": "Security", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS: list[dict] = []

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("vms.visitor.view", "See visitor records"),
    ("vms.visitor.register", "Register visitors at the gate"),
    ("vms.visit_request.create", "Submit a visit request"),
    ("vms.visit_request.approve", "Approve or reject visit requests"),
    ("vms.visit.view", "See visits and the on-site roster"),
    ("vms.visit.terminate", "Terminate a visit early"),
    ("vms.pass.view", "See visitor passes"),
    ("vms.pass.checkin", "Check a visitor in at the gate"),
    ("vms.pass.checkout", "Check a visitor out"),
    ("vms.pass.manage", "Issue and deactivate passes"),
    ("vms.gate.manage", "Close a gate for the day"),
    ("vms.zone.validate", "Validate zone access"),
    ("vms.zone.elevate", "Grant temporary zone elevation"),
    ("vms.blacklist.manage", "Maintain the blacklist and safe-list"),
    ("vms.policy.manage", "Configure access policies"),
    ("vms.muster.trigger", "Trigger and run an emergency muster"),
    ("vms.muster.view", "See muster rosters"),
    ("vms.alert.view", "See security alerts"),
    ("vms.alert.manage", "Close security alerts"),
    ("vms.report.view", "See VMS reports"),
    ("vms.role.manage", "Assign VMS operational roles"),
]

#: Keyed by the designation name as it exists in globals_designation.
_SUPER_ADMIN = [code for code, _ in PERMISSIONS]

_ADMIN = [
    "vms.visitor.view",
    "vms.visit.view",
    "vms.visit.terminate",
    "vms.pass.view",
    "vms.pass.manage",
    "vms.zone.validate",
    "vms.zone.elevate",
    "vms.blacklist.manage",
    "vms.policy.manage",
    "vms.muster.trigger",
    "vms.muster.view",
    "vms.alert.view",
    "vms.alert.manage",
    "vms.report.view",
    "vms.visit_request.approve",
]

_SECURITY = [
    "vms.visitor.view",
    "vms.visitor.register",
    "vms.visit.view",
    "vms.pass.view",
    "vms.pass.checkin",
    "vms.pass.checkout",
    "vms.pass.manage",
    "vms.gate.manage",
    "vms.zone.validate",
    "vms.muster.trigger",
    "vms.muster.view",
    "vms.alert.view",
    "vms.alert.manage",
]

_HOST = [
    "vms.visitor.view",
    "vms.visit_request.create",
    "vms.visit_request.approve",
    "vms.visit.view",
    "vms.visit.terminate",
    "vms.pass.view",
    "vms.muster.trigger",
    "vms.muster.view",
    "vms.alert.view",
]

ROLE_GRANTS = {
    "super_admin": _SUPER_ADMIN,
    "vms_admin": _ADMIN,
    "vms_security": _SECURITY,
    "host": _HOST,
}
