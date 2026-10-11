"""Employee Leave Management — registry.

ELM is the institute's leave platform for its *employees* (Faculty and
Staff). Everything a module must declare lives here: the sidebar entry,
the permission catalogue, and who holds each permission, keyed by the
designation name as it exists in ``globals_designation`` — the IAM seeds
its grants from ``registry/permissions.json``, which is generated from
this file by ``make permissions``.

Permission codes are exactly three segments (``elm.<resource>.<action>``)
and lowercase: the manifest's enforcement grep and the IAM's grant model
both assume that shape.
"""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.balances", "label": "My Balances",
     "icon": "FaChartBar", "to": "/elm/balances",
     "required_permission": "elm.leave.view_self", "sort_order": 5},
    {"code": "elm.requests", "label": "My Leave",
     "icon": "FaCalendarAlt", "to": "/elm/requests",
     "required_permission": "elm.leave.view_self", "sort_order": 10},
    {"code": "elm.tasks", "label": "My Tasks",
     "icon": "FaCheckDouble", "to": "/elm/tasks",
     "required_permission": "elm.leave.view_self", "sort_order": 20},
    {"code": "elm.records", "label": "Leave Records",
     "icon": "FaClipboardList", "to": "/elm/records",
     "required_permission": "elm.records.view", "sort_order": 30},
    {"code": "elm.calendar", "label": "Holiday Calendar",
     "icon": "FaCalendarAlt", "to": "/elm/calendar",
     "required_permission": "elm.leave.view_self", "sort_order": 40},
    {"code": "elm.offline", "label": "Offline Entry",
     "icon": "FaFileSignature", "to": "/elm/offline",
     "required_permission": "elm.records.offline", "sort_order": 50},
    {"code": "elm.config", "label": "Configuration",
     "icon": "FaCog", "to": "/elm/config",
     "required_permission": "elm.config.policy", "sort_order": 60},
]

# -- permission catalogue -----------------------------------------------------
# Every code below must appear verbatim in the module's own code (a view
# guard or a service-level authz check) — `permission_manifest --check`
# fails on a declared permission nothing enforces.

PERMISSIONS = [
    # employee (applicant) capabilities — EL-UC-001/007/008/009/010/012/013
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view_self", "View own leave balances and history"),
    ("elm.leave.withdraw", "Withdraw a pending leave request"),
    ("elm.leave.nominate", "Nominate or replace a substitute"),
    ("elm.leave.cancel", "Request cancellation of approved leave"),
    ("elm.leave.extend", "Request extension of ongoing EL/COL/VL"),
    ("elm.leave.resume", "Submit resumption of duty"),
    # substitute / responsibility holder — EL-UC-002
    ("elm.substitute.respond", "Accept or decline a substitute assignment"),
    # Unit Head — EL-UC-003 (final for CL/RH, recommendation otherwise)
    ("elm.review.unit_head", "Review leave requests at the Unit Head"),
    # Establishment processing role (Deputy Registrar (Estt.)) — EL-UC-004
    ("elm.review.establishment", "Verify and route higher-sanction requests"),
    # final Sanctioning Authority — EL-UC-005/011
    ("elm.sanction.final", "Make the final sanctioning decision"),
    ("elm.resume.review", "Review a resumption of duty"),
    # records — EL-UC-016/017
    ("elm.records.view", "View leave records within authorized scope"),
    ("elm.records.offline", "Record already-sanctioned offline leave"),
    ("elm.records.maintain", "Maintain authorized leave records"),
    # configuration — EL-UC-014/015/018
    ("elm.config.policy", "Maintain leave-policy parameters"),
    ("elm.config.hierarchy", "Maintain sanctioning hierarchy configuration"),
    ("elm.config.calendar", "Maintain and publish the holiday/RH calendar"),
    ("elm.config.units", "Maintain organizational units and Unit Heads"),
    ("elm.config.vacation", "Maintain the vacation-period projection"),
    ("elm.config.sla", "Configure workflow SLA thresholds"),
    # year-end — EL-UC-020
    ("elm.yearend.run", "Trigger year-end leave processing"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.task.notify",      # BR-EL-035: notify the assignee of a new task
    "elm.sla.process",      # EL-UC-021: reminder/escalation sweep
    "elm.yearend.process",  # EL-UC-020: event-triggered year-end run
]

# -- who holds what -----------------------------------------------------------
# Keys are designation names exactly as they exist in globals_designation;
# the IAM grants these when seeding. A person may hold several
# designations at once (globals_holdsdesignation), which is how a Head of
# Department is both an employee and a Unit Head.

_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.nominate",
    "elm.substitute.respond",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
]

_SANCTIONING = [
    "elm.sanction.final",
    "elm.resume.review",
    "elm.records.view",
]

ROLE_GRANTS = {
    # employees — the applicant pool (Faculty and Staff are the
    # employee categories; ELM serves no other kind)
    "Faculty": _EMPLOYEE,
    "Staff": _EMPLOYEE,
    "Assistant Professor": _EMPLOYEE,
    "Associate Professor": _EMPLOYEE,
    "Professor": _EMPLOYEE,
    # Unit Head: employee capabilities plus the review seat
    "Head of Department": [
        *_EMPLOYEE,
        "elm.review.unit_head",
        "elm.records.view",
    ],
    # Establishment processing role: routes, and may also sanction
    "Deputy Registrar (Estt.)": [
        *_EMPLOYEE,
        "elm.review.establishment",
        *_SANCTIONING,
    ],
    # competent final authorities
    "Dean": [*_EMPLOYEE, *_SANCTIONING],
    "Registrar": [*_EMPLOYEE, *_SANCTIONING],
    "Director": [*_EMPLOYEE, *_SANCTIONING],
    # Leave Administrator: record synchronization and configuration,
    # explicitly not sanctioning (BR-EL-037)
    "Leave Administrator": [
        "elm.records.view",
        "elm.records.offline",
        "elm.records.maintain",
        "elm.config.policy",
        "elm.config.hierarchy",
        "elm.config.calendar",
        "elm.config.units",
        "elm.config.vacation",
        "elm.config.sla",
        "elm.yearend.run",
    ],
}
