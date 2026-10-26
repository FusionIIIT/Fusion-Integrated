"""ELM module manifest, navigation, permissions, default hierarchy, and readiness."""
from __future__ import annotations

from modules.elm.domain import permissions as p

MODULE = {
    "code": "elm",
    "label": "Leave",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply for Leave", "icon": "Plus",
     "to": "/elm/apply", "required_permission": p.P_CREATE, "sort_order": 10},
    {"code": "elm.mine", "label": "My Leave", "icon": "CalendarBlank",
     "to": "/elm/mine", "required_permission": p.P_VIEW, "sort_order": 20},
    {"code": "elm.balances", "label": "Balances & History", "icon": "Wallet",
     "to": "/elm/balances", "required_permission": p.P_BALANCE, "sort_order": 30},
    {"code": "elm.substitutions", "label": "Substitutions", "icon": "Users",
     "to": "/elm/substitutions", "required_permission": p.P_SUBSTITUTE, "sort_order": 40},
    {"code": "elm.queue", "label": "Leave Approvals", "icon": "Checks",
     "to": "/elm/queue", "required_permission": p.P_REVIEW, "sort_order": 50},
    {"code": "elm.resumptions", "label": "Resumptions", "icon": "UserCheck",
     "to": "/elm/resumptions", "required_permission": p.P_RESUMPTION, "sort_order": 60},
    {"code": "elm.policies", "label": "Leave Policy", "icon": "Sliders",
     "to": "/elm/policies", "required_permission": p.P_POLICY, "sort_order": 70},
    {"code": "elm.calendar", "label": "Holiday Calendar", "icon": "Calendar",
     "to": "/elm/calendar", "required_permission": p.P_CALENDAR, "sort_order": 80},
    {"code": "elm.offline", "label": "Offline Leave", "icon": "ClipboardText",
     "to": "/elm/offline", "required_permission": p.P_OFFLINE, "sort_order": 90},
    {"code": "elm.accounts", "label": "Leave Accounts", "icon": "IdentificationCard",
     "to": "/elm/accounts", "required_permission": p.P_ACCOUNT_VIEW, "sort_order": 100},
]

PERMISSIONS = [
    (p.P_VIEW, "See one's own leave requests"),
    (p.P_CREATE, "Apply for leave or an extension"),
    (p.P_UPDATE, "Modify, cancel or resume one's own leave"),
    (p.P_WITHDRAW, "Withdraw one's own pending request"),
    (p.P_SUBSTITUTE, "Accept or decline a substitute nomination"),
    (p.P_BALANCE, "See one's own balances and leave-account history"),
    (p.P_REVIEW, "Review, recommend or forward routed leave"),
    (p.P_APPROVE, "Approve or reject leave as sanctioning authority"),
    (p.P_RESUMPTION, "Verify resumption of duty"),
    (p.P_POLICY, "Create, revise and publish leave policy and hierarchy"),
    (p.P_CALENDAR, "Create, revise and publish the holiday/RH calendar"),
    (p.P_OFFLINE, "Record offline-sanctioned leave"),
    (p.P_ACCOUNT_VIEW, "See any employee's leave account"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    p.P_VIEW,
    p.P_CREATE,
    p.P_UPDATE,
    p.P_WITHDRAW,
    p.P_SUBSTITUTE,
    p.P_BALANCE,
]

_UNIT_HEADS = [
    "HOD (CSE)",
    "HOD (ECE)",
    "HOD (ME)",
    "HOD (Design)",
    "HOD (NS)",
    "HOD (Liberal Arts)",
    "SectionHead_PS",
    "SectionHead_IWD",
    "SectionHead_RSPC",
    "SectionHead_HR",
]

_REVIEW_AND_APPROVE = [p.P_REVIEW, p.P_APPROVE, p.P_RESUMPTION]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Deputy Registrar": [p.P_REVIEW, p.P_RESUMPTION],
    "Registrar": _REVIEW_AND_APPROVE,
    "Director": _REVIEW_AND_APPROVE,
    **dict.fromkeys(_UNIT_HEADS, _REVIEW_AND_APPROVE),
    "Leave Administrator": [
        p.P_POLICY,
        p.P_CALENDAR,
        p.P_OFFLINE,
        p.P_ACCOUNT_VIEW,
    ],
}

DEFAULT_HIERARCHY: dict = {
    "unit_heads": {
        "CSE": "HOD (CSE)",
        "ECE": "HOD (ECE)",
        "ME": "HOD (ME)",
        "Design": "HOD (Design)",
        "NS": "HOD (NS)",
        "Liberal Arts": "HOD (Liberal Arts)",
        "PS": "SectionHead_PS",
        "IWD": "SectionHead_IWD",
        "RSPC": "SectionHead_RSPC",
        "HR": "SectionHead_HR",
    },
    "establishment_role": "Deputy Registrar",
    "sanctioning": {
        "faculty": {"default": "Director"},
        "staff": {"default": "Registrar"},
    },
    "director_role": "Director",
    "resumption_verifier": "unit_head",
    "sla": {},
}


def readiness() -> list[str]:
    from modules.elm.selectors.config import effective_policy_version

    unmet: list[str] = []
    if effective_policy_version() is None:
        unmet.append("no published ELM policy version (run 'manage.py seed_elm_policy')")
    return unmet
