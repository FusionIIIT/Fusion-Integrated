"""ELM module manifest; the IAM derives module grants and navigation from this."""
MODULE = {
    "code": "elm", "label": "Leave", "icon": "FaCalendarAlt",
    "base_path": "/elm", "nav_section": "Services", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.my-leave", "label": "My Leave", "icon": "FaCalendarAlt", "to": "/elm", "required_permission": "elm.leave_request.view", "sort_order": 10},
    {"code": "elm.review-queue", "label": "Leave Review Queue", "icon": "FaClipboardCheck", "to": "/elm/queue", "required_permission": "elm.leave_request.review", "sort_order": 20},
    {"code": "elm.leave-balances", "label": "Leave Balances", "icon": "FaIdCard", "to": "/elm/balances", "required_permission": "elm.leave_balance.view", "sort_order": 30},
    {"code": "elm.resumptions", "label": "Resumption Review", "icon": "FaExternalLinkAlt", "to": "/elm/resumptions", "required_permission": "elm.resumption.review", "sort_order": 35},
    {"code": "elm.leave-admin", "label": "Leave Administration", "icon": "FaCog", "to": "/elm/admin", "required_permission": "elm.policy.manage", "sort_order": 40},
]

PERMISSIONS = [
    ("elm.leave_request.view", "View own leave requests"),
    ("elm.leave_request.view_all", "View all employee leave requests"),
    ("elm.leave_request.create", "Submit leave requests and extensions"),
    ("elm.leave_request.delete", "Withdraw pending leave requests"),
    ("elm.leave_request.update", "Request cancellation, substitute changes, and resumption"),
    ("elm.leave_request.review", "Review and recommend on assigned leave requests"),
    ("elm.leave_request.approve", "Approve or reject assigned leave requests"),
    ("elm.substitution.review", "Respond to substitute requests"),
    ("elm.resumption.review", "Verify employee resumption records"),
    ("elm.leave_balance.view", "View own leave balances and history"),
    ("elm.policy.manage", "Maintain current leave policy and hierarchy configuration"),
    ("elm.calendar.publish", "Maintain and publish holiday/RH/vacation calendars"),
    ("elm.offline_record.create", "Record already-sanctioned offline leave"),
]
SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["elm.leave_request.view", "elm.leave_request.create", "elm.leave_request.delete", "elm.leave_request.update", "elm.leave_balance.view", "elm.substitution.review"]
_UNIT_HEAD = [*_EMPLOYEE, "elm.leave_request.review", "elm.leave_request.approve", "elm.resumption.review"]
_ADMIN = [*_EMPLOYEE, "elm.leave_request.view_all", "elm.leave_request.review", "elm.leave_request.approve", "elm.resumption.review", "elm.policy.manage", "elm.calendar.publish", "elm.offline_record.create"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,
    "SectionHead_PS": _UNIT_HEAD,
    "SectionHead_IWD": _UNIT_HEAD,
    "SectionHead_RSPC": _UNIT_HEAD,
    "SectionHead_HR": _UNIT_HEAD,
    "Deputy Registrar": _UNIT_HEAD,
    "Registrar": _ADMIN,
    "Director": _ADMIN,
    "Leave Administrator": _ADMIN,
}


def readiness() -> list[str]:
    """Keep ELM planned until its current policy row has been seeded."""
    try:
        from modules.elm.models import LeavePolicy
        if not LeavePolicy.objects.filter(key="current").exists():
            return ["run manage.py seed_elm_policy before activating ELM"]
    except Exception as exc:  # noqa: BLE001 - registry readiness must report a prerequisite, not crash seeding
        return [f"ELM policy storage is not ready: {exc.__class__.__name__}"]
    return []
