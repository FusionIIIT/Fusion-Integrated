"""What the server tells the shell and the IAM about Visitor Management (ADR-0010).

All 33 permission codes are declared here once (31 + 2 system). Lanes enforce
them; they never add to this list (build_sequence/13_schema_and_ownership.md).

Visitors themselves are NOT IAM principals (decision D-1): their endpoints use
the OTP session cookie and are deliberately absent from ROLE_GRANTS.
"""

MODULE = {
    "code": "vms", "label": "Visitors", "icon": "IdentificationBadge",
    "base_path": "/vms", "nav_section": "Visitors", "sort_order": 40,
    "status": "planned",   # stays planned until Phase 3 ships the screens
}

#: The screens the Phase 3 UI will need. They are parked here, not in NAV_ITEMS,
#: because ops/checks/nav_matches_routes.py fails any nav item that has no client
#: route (client/src/modules/vms does not exist yet). Phase 3 renames this to
#: NAV_ITEMS in the same change that adds routes.tsx.
PLANNED_NAV_ITEMS = [
    {"code": "vms.visits", "label": "My Visits", "icon": "UsersThree",
     "to": "/vms/visits", "required_permission": "vms.notification.view_self",
     "sort_order": 10},
    {"code": "vms.approvals", "label": "Approvals", "icon": "Stamp",
     "to": "/vms/approvals", "required_permission": "vms.request.view_assigned",
     "sort_order": 20},
    {"code": "vms.gate", "label": "Gate", "icon": "Door",
     "to": "/vms/gate", "required_permission": "vms.gate.operate",
     "sort_order": 30},
    {"code": "vms.roster", "label": "Roster", "icon": "ListChecks",
     "to": "/vms/roster", "required_permission": "vms.monitor.view",
     "sort_order": 40},
    {"code": "vms.muster", "label": "Muster", "icon": "Siren",
     "to": "/vms/muster", "required_permission": "vms.muster.rollcall",
     "sort_order": 50},
    {"code": "vms.events", "label": "Events", "icon": "CalendarStar",
     "to": "/vms/events", "required_permission": "vms.event.manage",
     "sort_order": 60},
    {"code": "vms.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/vms/reports", "required_permission": "vms.report.view",
     "sort_order": 70},
    {"code": "vms.admin", "label": "Administration", "icon": "Gear",
     "to": "/vms/admin", "required_permission": "vms.policy.manage",
     "sort_order": 80},
]

NAV_ITEMS = []

_HOST = [
    ("vms.request.decide", "Approve or reject a visit request for oneself"),
    ("vms.request.view_assigned", "See visit requests assigned to oneself"),
    ("vms.preauth.manage", "Pre-authorise recurring visitors"),
    ("vms.pass.terminate", "Terminate a visitor's pass early"),
]
_ANY = [
    ("vms.notification.view_self", "See one's own VMS notifications"),
]
_SECURITY = [
    ("vms.walkin.register", "Register a walk-in visitor at the gate"),
    ("vms.gate.operate", "Check visitors in and out at the gate"),
    ("vms.gate.escalate", "Escalate a gate denial to an Admin"),
    ("vms.gate.sync", "Upload offline gate events"),
    ("vms.muster.trigger", "Trigger an emergency muster"),
    ("vms.muster.rollcall", "Mark visitors accounted for during a muster"),
    ("vms.monitor.view", "See live occupancy, roster and alerts"),
]
_ADMIN = [
    ("vms.walkin.contingency_decide", "Decide a walk-in when the host is unavailable"),
    ("vms.urgent.decide", "Decide a same-day urgent request"),
    ("vms.extension.decide", "Approve or reject a visit extension"),
    ("vms.gate.override", "Override an eligible gate denial"),
    ("vms.zone.elevate", "Grant a time-boxed zone elevation"),
    ("vms.zone.manage", "Maintain zones and gates"),
    ("vms.blacklist.manage", "Maintain the visitor blacklist"),
    ("vms.blacklist.publish", "Publish a blacklist version"),
    ("vms.safelist.manage", "Maintain the visitor safe-list"),
    ("vms.policy.manage", "Edit a draft access policy"),
    ("vms.policy.publish", "Publish an access policy version"),
    ("vms.event.manage", "Create and manage event batches"),
    ("vms.report.view", "See anonymised visitor reports"),
    ("vms.report.export", "Export visitor reports"),
]
#: vms.report.view_pii is DANGEROUS (D-9: reveals un-masked visitor identity).
#: The registry/manifest format has no per-permission is_dangerous flag today,
#: so the label carries the warning and the IAM must flag it when seeding.
_SUPER_ADMIN = [
    ("vms.report.view_pii", "DANGEROUS: see un-masked visitor identity in reports"),
    ("vms.role.assign", "Assign Admin and Security roles and scopes"),
    ("vms.integration.manage", "Maintain integration settings"),
    ("vms.vip.manage", "Grant and revoke VIP permissions"),
    ("vms.audit.view", "Read the VMS audit log"),
]
_SYSTEM = [
    ("vms.visit.auto_checkout", "System auto-checkout at pass expiry"),
    ("vms.request.auto_expire", "System expiry of unanswered requests"),
]

#: Admins terminate passes too (UC-036), and event revoke/cancel reach the same
#: service (service request g-3), so Admin designations are granted the host
#: permission as well. It is listed once, under _HOST, in PERMISSIONS.
_ADMIN_TERMINATE = [("vms.pass.terminate", "Terminate a visitor's pass early")]

PERMISSIONS = _HOST + _ANY + _SECURITY + _ADMIN + _SUPER_ADMIN + _SYSTEM

#: Performed by scheduled work, so no designation holds them.
SYSTEM_PERMISSIONS = [code for code, _ in _SYSTEM]


def _codes(*groups):
    return [code for group in groups for code, _ in group]


#: D-3. Keyed by designation name exactly as globals_designation holds it.
#: Time/zone scoping lives in RoleAssignment; IAM only grants the permission.
ROLE_GRANTS = {
    "faculty": _codes(_HOST, _ANY),                    # host, implicit (BR-185)
    "staff": _codes(_HOST, _ANY),
    "vms_security": _codes(_SECURITY, _ANY),           # new ERP designation
    "Registrar": _codes(_ADMIN, _ANY, _ADMIN_TERMINATE),
    "acadadmin": _codes(_ADMIN, _ANY, _ADMIN_TERMINATE),
    "Director": _codes(_ADMIN, _SUPER_ADMIN, _ANY, _ADMIN_TERMINATE),    # Super Admin
}
