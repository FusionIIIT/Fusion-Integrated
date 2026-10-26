"""What the server tells the shell about this module (ADR-0010).

Permissions follow `<module>.<resource>.<action>`; ROLE_GRANTS says which
designation holds each one, keyed by the designation name as it exists in
globals_designation. A permission nobody holds is a link nobody can click, so
`manage.py permission_manifest --check` refuses it.
"""
MODULE = {
    "code": "leave", "label": "Leave Management", "icon": "FaCalendarCheck",
    "base_path": "/leave", "nav_section": "Administration", "sort_order": 20,
    # Planned until the last sub-phase lands; an ungranted, unroutable module
    # is the safe way to ship work in progress.
    "status": "planned",
    # Employee leave has always lived in the ERP's `hr` module column.
    "legacy_column_name": "hr",
}

NAV_ITEMS = [
    # -- the employee's own screens -----------------------------------------
    {"code": "leave.mine", "label": "My Leave", "icon": "FaPlaneDeparture",
     "to": "/leave/mine", "required_permission": "leave.application.view_self",
     "sort_order": 5},
    {"code": "leave.substitutions", "label": "Substitutions",
     "icon": "FaUserFriends", "to": "/leave/substitutions",
     "required_permission": "leave.substitute.respond", "sort_order": 10},

    # -- the processing lanes ------------------------------------------------
    {"code": "leave.inbox", "label": "Leave Inbox", "icon": "FaInbox",
     "to": "/leave/inbox", "required_permission": "leave.request.review",
     "sort_order": 20},
    {"code": "leave.team", "label": "All Leave", "icon": "FaUsers",
     "to": "/leave/team", "required_permission": "leave.application.view",
     "sort_order": 30},

    # -- configuration -------------------------------------------------------
    {"code": "leave.administration", "label": "Administration",
     "icon": "FaSlidersH", "to": "/leave/administration",
     "required_permission": "leave.policy.manage", "sort_order": 40},
]

#: Every permission this module recognises.
PERMISSIONS = [
    ("leave.application.view_self", "See one's own leave requests"),
    ("leave.application.view", "See every leave request, within scope"),
    ("leave.application.create", "Apply for leave"),
    ("leave.application.withdraw", "Withdraw a pending request"),
    ("leave.application.cancel", "Request cancellation of approved leave"),
    ("leave.application.extend", "Request an extension of ongoing leave"),
    ("leave.substitute.respond", "Accept or decline a nominated substitution"),
    ("leave.substitute.nominate", "Nominate a replacement substitute"),
    ("leave.request.review", "Review at Unit Head and record a recommendation"),
    ("leave.request.route", "Verify and route a higher-sanction request"),
    ("leave.request.approve", "Take the final sanctioning decision"),
    ("leave.resumption.submit", "Submit a resumption of duty"),
    ("leave.resumption.review", "Review a submitted resumption"),
    ("leave.balance.view", "See one's own leave balances"),
    ("leave.calendar.manage", "Maintain and publish the holiday/RH calendar"),
    ("leave.policy.manage", "Maintain leave policy and hierarchy configuration"),
    ("leave.record.manage", "Maintain leave records and enter offline leave"),
]

#: Performed by a scheduled command, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave.year_end.process",
    "leave.sla.process",
]

# -- role grants ---------------------------------------------------------------
# Every employee holds the same starting set: ELM is about your own leave, and
# the designation only decides what you process for other people.
_EMPLOYEE = [
    "leave.application.view_self",
    "leave.application.create",
    "leave.application.withdraw",
    "leave.application.cancel",
    "leave.application.extend",
    "leave.substitute.respond",
    "leave.substitute.nominate",
    "leave.resumption.submit",
    "leave.balance.view",
]

#: A Unit Head reviews and recommends (BR-EL-016/017).
_UNIT_HEAD = [*_EMPLOYEE, "leave.request.review", "leave.application.view"]

#: The Establishment processing role routes on, and is an employee too.
_ESTABLISHMENT = [*_EMPLOYEE, "leave.request.route", "leave.application.view"]

#: A final Sanctioning Authority decides, and still takes their own leave.
_AUTHORITY = [
    *_EMPLOYEE, "leave.request.approve", "leave.resumption.review",
    "leave.application.view",
]

#: The leave administrator: configuration and records, never a second sanction.
_ADMINISTRATOR = [
    *_EMPLOYEE, "leave.policy.manage", "leave.calendar.manage",
    "leave.record.manage", "leave.application.view",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Professor": _EMPLOYEE,
    "Associate Professor": _EMPLOYEE,
    "Assistant Professor": _EMPLOYEE,
    "Junior Assistant": _EMPLOYEE,
    "Senior Assistant": _EMPLOYEE,
    "Upper Division Clerk": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Dean Academic": _AUTHORITY,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "acadadmin": _ADMINISTRATOR,
}
