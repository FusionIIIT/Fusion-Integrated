"""What the server tells the shell about Employee Leave Management (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = [
    # --- Employee Self-Service ---
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "leave_elm.leave_request.create",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Requests",
        "icon": "ClockCounterClockwise",
        "to": "/elm/mine",
        "required_permission": "leave_elm.leave_request.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.balance",
        "label": "Leave Balance & History",
        "icon": "ChartPieSlice",
        "to": "/elm/balance",
        "required_permission": "leave_elm.leave_balance.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.substitute_tasks",
        "label": "Substitute Responses",
        "icon": "UserSwitch",
        "to": "/elm/substitute-requests",
        "required_permission": "leave_elm.substitute.respond",
        "sort_order": 40,
    },

    # --- Approval & Review Pipeline ---
    {
        "code": "elm.unit_head",
        "label": "Unit Head Review",
        "icon": "CheckSquare",
        "to": "/elm/unit-head-review",
        "required_permission": "leave_elm.leave_request.review",
        "sort_order": 50,
    },
    {
        "code": "elm.establishment",
        "label": "Establishment Routing",
        "icon": "FlowArrow",
        "to": "/elm/establishment-routing",
        "required_permission": "leave_elm.leave_request.route",
        "sort_order": 60,
    },
    {
        "code": "elm.sanction",
        "label": "Sanction Decisions",
        "icon": "SealCheck",
        "to": "/elm/sanction-decisions",
        "required_permission": "leave_elm.leave_request.approve",
        "sort_order": 70,
    },

    # --- Administration & Records ---
    {
        "code": "elm.policy",
        "label": "Leave Policy Admin",
        "icon": "Gear",
        "to": "/elm/admin/policy",
        "required_permission": "leave_elm.leave_policy.manage",
        "sort_order": 80,
    },
    {
        "code": "elm.holidays",
        "label": "Holiday Calendar",
        "icon": "CalendarBlank",
        "to": "/elm/admin/holidays",
        "required_permission": "leave_elm.holiday_calendar.manage",
        "sort_order": 90,
    },
    {
        "code": "elm.offline_record",
        "label": "Offline Leaves",
        "icon": "FilePlus",
        "to": "/elm/offline-records",
        "required_permission": "leave_elm.leave_record.record_offline",
        "sort_order": 100,
    },
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave_elm.leave_request.create", "Apply for a leave or extension"),
    ("leave_elm.leave_request.view_self", "View own leave requests and details"),
    ("leave_elm.leave_request.update", "Withdraw or update pending leave request"),
    ("leave_elm.leave_request.view", "View leave requests within unit/institutional scope"),
    ("leave_elm.leave_request.review", "Review and recommend higher-sanction requests at Unit Head"),
    ("leave_elm.leave_request.route", "Verify and route higher-sanction leave in Establishment"),
    ("leave_elm.leave_request.approve", "Sanction or reject leave and cancellation requests"),
    ("leave_elm.leave_balance.view_self", "View own leave balances and credit history"),
    ("leave_elm.leave_balance.manage", "Credit, carry forward, or adjust employee leave balances"),
    ("leave_elm.substitute.respond", "Accept or decline nominated substitute responsibility"),
    ("leave_elm.leave_policy.manage", "Configure leave rules and entitlements"),
    ("leave_elm.holiday_calendar.manage", "Publish and maintain RH and closed holiday calendar"),
    ("leave_elm.leave_record.record_offline", "Record offline-sanctioned leave entries"),
    ("leave_elm.leave_request.auto_escalate", "Automated SLA escalation"),
]

#: Performed by background tasks / scheduler, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave_elm.leave_request.auto_escalate",
]

# Basic employee grants (applies to faculty and staff)
_EMPLOYEE = [
    "leave_elm.leave_request.create",
    "leave_elm.leave_request.view_self",
    "leave_elm.leave_request.update",
    "leave_elm.leave_balance.view_self",
    "leave_elm.substitute.respond",
]

# Unit Head role (e.g. HOD, Section Head)
_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave_elm.leave_request.view",
    "leave_elm.leave_request.review",
    "leave_elm.leave_request.approve",  # Final sanction for CL/RH
]

# Establishment section / assistant registrar
_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave_elm.leave_request.view",
    "leave_elm.leave_request.route",
    "leave_elm.leave_balance.manage",
    "leave_elm.leave_record.record_offline",
]

# Sanctioning Authorities (Deans, Registrar, Director)
_SANCTIONING_AUTHORITY = [
    *_EMPLOYEE,
    "leave_elm.leave_request.view",
    "leave_elm.leave_request.approve",
]

# Leave Administrator (Super-admin / policy manager)
_LEAVE_ADMIN = [
    *_ESTABLISHMENT,
    "leave_elm.leave_policy.manage",
    "leave_elm.holiday_calendar.manage",
]

#: Keyed by designation name as it exists in globals_designation / IAM roles.
ROLE_GRANTS = {
    # Basic institute roles
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,

    # Unit heads
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,

    # Administration and higher sanctioning authorities
    "Dean Academic": _SANCTIONING_AUTHORITY,
    "Dean Students": _SANCTIONING_AUTHORITY,
    "Dean R&D": _SANCTIONING_AUTHORITY,
    "Registrar": _SANCTIONING_AUTHORITY,
    "Director": _SANCTIONING_AUTHORITY,

    # Establishment & administration
    "Assistant Registrar": _ESTABLISHMENT,
    "acadadmin": _LEAVE_ADMIN,
}
