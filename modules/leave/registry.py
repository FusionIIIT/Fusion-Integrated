"""What the server tells the shell and the IAM about Leave (ADR-0010)."""

MODULE = {
    "code": "leave", "label": "Leave", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "CalendarCheck",
     "to": "/leave/mine", "required_permission": "leave.request.view", "sort_order": 10},
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "CalendarPlus",
     "to": "/leave/apply", "required_permission": "leave.request.create", "sort_order": 20},
    {"code": "leave.substitutions", "label": "Substitute Requests", "icon": "UserSwitch",
     "to": "/leave/substitutions", "required_permission": "leave.substitution.review",
     "sort_order": 30},
    {"code": "leave.queue", "label": "Leave Approvals", "icon": "Stamp",
     "to": "/leave/approvals", "required_permission": "leave.request.review", "sort_order": 40},
    {"code": "leave.records", "label": "Leave Records", "icon": "Archive",
     "to": "/leave/records", "required_permission": "leave.record.view", "sort_order": 60},
    {"code": "leave.calendar", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/leave/calendar", "required_permission": "leave.calendar.update", "sort_order": 70},
    {"code": "leave.policy", "label": "Leave Policy", "icon": "Sliders",
     "to": "/leave/policy", "required_permission": "leave.policy.update", "sort_order": 80},
    {"code": "leave.hierarchy", "label": "Approval Hierarchy", "icon": "TreeStructure",
     "to": "/leave/hierarchy", "required_permission": "leave.hierarchy.update",
     "sort_order": 85},
    {"code": "leave.sla", "label": "Response Deadlines", "icon": "Timer",
     "to": "/leave/sla", "required_permission": "leave.sla.update", "sort_order": 90},
]

PERMISSIONS = [
    ("leave.request.create", "Apply for leave, and ask to cancel, extend or resume it"),
    ("leave.request.view", "See one's own leave requests"),
    ("leave.request.revoke", "Withdraw one's own pending request"),
    ("leave.request.export", "Print or export a leave application"),
    ("leave.balance.view", "See one's own balances and ledger"),
    ("leave.substitution.review", "Accept or decline covering for a colleague"),
    ("leave.request.review", "Review leave as a Unit Head, and see an approvals queue"),
    ("leave.request.assign", "Verify and route higher-sanction leave (Establishment)"),
    ("leave.request.approve", "Sanction or reject leave as the final authority"),
    ("leave.resumption.review", "Review a resumption of duty"),
    ("leave.policy.update", "Revise the leave policy parameters"),
    ("leave.hierarchy.update", "Revise Unit Heads and sanctioning routes"),
    ("leave.calendar.update", "Edit the holiday calendar and vacation periods"),
    ("leave.calendar.publish", "Publish a holiday calendar"),
    ("leave.sla.update", "Set response deadlines and escalation"),
    ("leave.record.view", "See every employee's leave record"),
    ("leave.record.import", "Record leave sanctioned offline"),
    ("leave.record.update", "Correct a balance by an administrative entry"),
    ("leave.ledger.manage", "System year-end and annual credit"),
    ("leave.task.assign", "System SLA reassignment"),
]

#: Performed by scheduled work, so no designation holds them.
SYSTEM_PERMISSIONS = ["leave.ledger.manage", "leave.task.assign"]

_EMPLOYEE = ["leave.request.create", "leave.request.view", "leave.request.revoke",
             "leave.request.export", "leave.balance.view", "leave.substitution.review"]
_UNIT_HEAD = ["leave.request.review", "leave.request.export"]
_ESTABLISHMENT = ["leave.request.review", "leave.request.assign", "leave.request.approve",
                  "leave.resumption.review", "leave.request.export"]
_AUTHORITY = ["leave.request.review", "leave.request.approve", "leave.resumption.review",
              "leave.request.export"]
_ADMIN = ["leave.policy.update", "leave.hierarchy.update", "leave.calendar.update",
          "leave.calendar.publish", "leave.sla.update", "leave.record.view",
          "leave.record.import", "leave.record.update", "leave.request.export"]

#: Keyed by the designation name exactly as globals_designation holds it.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,
    "SectionHead_HR": _UNIT_HEAD,
    "SectionHead_IWD": _UNIT_HEAD,
    "SectionHead_PS": _UNIT_HEAD,
    "SectionHead_RSPC": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "Dean_s": _AUTHORITY,
    "Dean Academic": _AUTHORITY,
    "Dean (P&D)": _AUTHORITY,
    "Dean (R&D)": _AUTHORITY,
    "dean_rspc": _AUTHORITY,
    "hradmin": _ADMIN,
}


def readiness() -> list[str]:
    """The unmet prerequisites, each named; an empty list means Leave can be switched on."""
    from modules.leave.services.readiness import unmet

    return unmet()
