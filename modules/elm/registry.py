"""What the server tells the shell about ELM (ADR-0010)."""
MODULE = {
    "code": "elm", "label": "Leave Management", "icon": "CalendarCheck",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

# ponytail: backend only; nav items land with the client routes (nav_matches_routes.py).
NAV_ITEMS = []

PERMISSIONS = [
    ("elm.leave_request.view", "See one's own leave balances and history"),
    ("elm.leave_request.create",
     "Apply, withdraw, cancel, extend, resume, and answer substitute requests"),
    ("elm.leave_task.view", "See leave tasks assigned to you"),
    ("elm.leave_request.review", "Unit Head decision or recommendation"),
    ("elm.leave_request.assign", "Establishment verification and routing"),
    ("elm.leave_request.approve", "Final sanction and resumption review"),
    ("elm.policy.update", "Maintain leave policy, hierarchy and SLA"),
    ("elm.holiday_calendar.publish", "Maintain and publish the holiday/RH calendar"),
    ("elm.leave_record.create", "Record offline-sanctioned leave and corrections"),
    ("elm.leave_account.update", "System year-end and SLA processing"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave_account.update",
]

_EMPLOYEE = ["elm.leave_request.view", "elm.leave_request.create"]
_UNIT_HEAD = ["elm.leave_task.view", "elm.leave_request.review"]
_ESTABLISHMENT = ["elm.leave_task.view", "elm.leave_request.assign",
                  "elm.leave_request.approve"]
_AUTHORITY = ["elm.leave_task.view", "elm.leave_request.approve"]
_ADMIN = ["elm.policy.update", "elm.holiday_calendar.publish",
          "elm.leave_record.create"]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,
    "SectionHead_HR": _UNIT_HEAD,
    "SectionHead_IWD": _UNIT_HEAD,
    "SectionHead_PS": _UNIT_HEAD,
    "SectionHead_RSPC": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Dean Academic": _AUTHORITY,
    "Dean (P&D)": _AUTHORITY,
    "Dean (R&D)": _AUTHORITY,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "hradmin": _ADMIN,
}
