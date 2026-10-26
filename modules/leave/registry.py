"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave_management",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- employee -----------------------------------------------------------
    {"code": "leave.apply", "label": "Apply for Leave",
     "icon": "FaFileAlt", "to": "/leave/apply",
     "required_permission": "leave_management.leave_request.create",
     "sort_order": 5},
    {"code": "leave.my_requests", "label": "My Leave Requests",
     "icon": "FaListAlt", "to": "/leave/my-requests",
     "required_permission": "leave_management.leave_request.view_self",
     "sort_order": 10},
    {"code": "leave.balance", "label": "Leave Balance",
     "icon": "FaBalanceScale", "to": "/leave/balance",
     "required_permission": "leave_management.leave_balance.view_self",
     "sort_order": 15},
    {"code": "leave.history", "label": "Leave History",
     "icon": "FaHistory", "to": "/leave/history",
     "required_permission": "leave_management.leave_request.view_self",
     "sort_order": 20},

    # -- approver (Unit Head / Establishment) -------------------------------
    {"code": "leave.pending_approvals", "label": "Pending Approvals",
     "icon": "FaClock", "to": "/leave/pending-approvals",
     "required_permission": "leave_management.leave_request.approve",
     "sort_order": 50},
    {"code": "leave.substitute_requests", "label": "Substitute Requests",
     "icon": "FaUserCheck", "to": "/leave/substitute-requests",
     "required_permission": "leave_management.substitute_request.respond",
     "sort_order": 55},

    # -- administrator ------------------------------------------------------
    {"code": "leave.policy", "label": "Leave Policy",
     "icon": "FaCogs", "to": "/leave/policy",
     "required_permission": "leave_management.leave_policy.manage",
     "sort_order": 80},
    {"code": "leave.calendar", "label": "Holiday & RH Calendar",
     "icon": "FaCalendar", "to": "/leave/calendar",
     "required_permission": "leave_management.holiday_calendar.manage",
     "sort_order": 85},
    {"code": "leave.offline_entry", "label": "Record Offline Leave",
     "icon": "FaFileImport", "to": "/leave/offline-entry",
     "required_permission": "leave_management.offline_leave.record",
     "sort_order": 90},
    {"code": "leave.year_end", "label": "Year-End Processing",
     "icon": "FaChartBar", "to": "/leave/reports",
     "required_permission": "leave_management.year_end.process",
     "sort_order": 95},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    # Leave Request permissions
    ("leave_management.leave_request.create", "Submit a leave request"),
    ("leave_management.leave_request.view_self", "View own leave requests"),
    ("leave_management.leave_request.view", "View all leave requests (within scope)"),
    ("leave_management.leave_request.modify_pending", "Modify own pending leave request"),
    ("leave_management.leave_request.withdraw_pending", "Withdraw own pending leave request"),
    ("leave_management.leave_request.cancel_approved", "Request cancellation of approved leave"),
    ("leave_management.leave_request.extend", "Submit leave extension"),
    ("leave_management.leave_request.resume", "Submit resumption of duty"),
    ("leave_management.leave_request.approve", "Approve/reject leave requests"),
    ("leave_management.leave_request.view_audit", "View leave request audit trail"),

    # Leave Balance permissions
    ("leave_management.leave_balance.view_self", "View own leave balance"),
    ("leave_management.leave_balance.view", "View leave balances (within scope)"),
    ("leave_management.leave_balance.adjust", "Adjust leave balances (admin)"),

    # Substitute Request permissions
    ("leave_management.substitute_request.create", "Nominate a substitute"),
    ("leave_management.substitute_request.respond", "Accept/decline substitute nomination"),
    ("leave_management.substitute_request.view_self", "View substitute nominations for self"),

    # Leave Policy permissions
    ("leave_management.leave_policy.manage", "Maintain leave policy parameters"),
    ("leave_management.leave_policy.view", "View leave policy parameters"),

    # Holiday & RH Calendar permissions
    ("leave_management.holiday_calendar.manage", "Maintain holiday and RH calendar"),
    ("leave_management.holiday_calendar.view", "View holiday and RH calendar"),

    # Offline Leave permissions
    ("leave_management.offline_leave.record", "Record offline-sanctioned leave"),
    ("leave_management.offline_leave.view", "View offline-sanctioned leave entries"),

    # Year-end processing
    ("leave_management.year_end.process", "Run year-end leave processing"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave_management.leave_request.auto_expire",
    "leave_management.leave_request.sla_reminder",
    "leave_management.leave_request.sla_escalation",
]

_EMPLOYEE = [
    "leave_management.leave_request.create",
    "leave_management.leave_request.view_self",
    "leave_management.leave_request.modify_pending",
    "leave_management.leave_request.withdraw_pending",
    "leave_management.leave_request.cancel_approved",
    "leave_management.leave_request.extend",
    "leave_management.leave_request.resume",
    "leave_management.leave_balance.view_self",
    "leave_management.substitute_request.create",
    "leave_management.substitute_request.view_self",
    "leave_management.holiday_calendar.view",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave_management.leave_request.view",
    "leave_management.leave_request.approve",
    "leave_management.leave_balance.view",
    "leave_management.substitute_request.respond",
    "leave_management.leave_request.view_audit",
]

_ESTABLISHMENT = [
    *_UNIT_HEAD,
    "leave_management.leave_policy.view",
    "leave_management.holiday_calendar.view",
    "leave_management.offline_leave.view",
]

_LEAVE_ADMIN = [
    *_ESTABLISHMENT,
    "leave_management.leave_policy.manage",
    "leave_management.holiday_calendar.manage",
    "leave_management.offline_leave.record",
    "leave_management.leave_balance.adjust",
    "leave_management.year_end.process",
]

#: Keyed by the role name IAM resolves for a person.
#:
#: `faculty` is the basic role IAM derives from the ERP's user_type, not a
#: designation: build_session puts it in `roles` for every faculty member, so
#: this one entry reaches all teaching staff and no student or staff member.
#: The rest are the real designation names from globals_designation — the
#: previous keys (`employee`, `unit_head`, `leave_administrator`, ...) did not
#: exist in the ERP, which left every leave endpoint unreachable.
ROLE_GRANTS = {
    # Every faculty member: employee self-service screens.
    "faculty": _EMPLOYEE,

    # Unit Head review — HODs are faculty-only roles in IAM's catalogue.
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,

    # Establishment review — senior faculty offices.
    "Dean (R&D)": _ESTABLISHMENT,
    "Dean (P&D)": _ESTABLISHMENT,
    "Dean_s": _ESTABLISHMENT,
    "Director": _ESTABLISHMENT,

    # Leave administration sits with the Dean (Academic), who is faculty.
    # Registrar/Deputy Registrar are deliberately NOT granted: they are
    # faculty-or-staff offices, and this module is faculty-only.
    "Dean Academic": _LEAVE_ADMIN,
}