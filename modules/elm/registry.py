"""What the server tells the shell about ELM (ADR-0010); roles follow the spec's actors."""
from modules.elm.domain import permissions as p

MODULE = {
    "code": "elm", "label": "Leave Management", "icon": "CalendarCheck",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply for Leave", "icon": "PaperPlaneTilt",
     "to": "/elm/apply", "required_permission": p.P_CREATE, "sort_order": 10},
    {"code": "elm.mine", "label": "My Leave", "icon": "ListChecks",
     "to": "/elm/mine", "required_permission": p.P_VIEW, "sort_order": 20},
    {"code": "elm.balances", "label": "Balances & History", "icon": "Wallet",
     "to": "/elm/balances", "required_permission": p.P_BALANCE, "sort_order": 30},
    {"code": "elm.substitutions", "label": "Substitution Requests", "icon": "UserSwitch",
     "to": "/elm/substitutions", "required_permission": p.P_SUBSTITUTE, "sort_order": 40},
    {"code": "elm.queue", "label": "Leave Approvals", "icon": "Stamp",
     "to": "/elm/queue", "required_permission": p.P_REVIEW, "sort_order": 50},
    {"code": "elm.resumptions", "label": "Resumptions", "icon": "SignIn",
     "to": "/elm/resumptions", "required_permission": p.P_RESUMPTION, "sort_order": 60},
    {"code": "elm.policies", "label": "Leave Policy", "icon": "Sliders",
     "to": "/elm/policies", "required_permission": p.P_POLICY, "sort_order": 70},
    {"code": "elm.calendar", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/elm/calendar", "required_permission": p.P_CALENDAR, "sort_order": 80},
    {"code": "elm.offline", "label": "Offline Leave", "icon": "Archive",
     "to": "/elm/offline", "required_permission": p.P_OFFLINE, "sort_order": 90},
    {"code": "elm.accounts", "label": "Leave Accounts", "icon": "BookOpen",
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

SYSTEM_PERMISSIONS = [p.P_YEAR_END, p.P_SLA]

SCOPE_PERMISSIONS = [p.P_VIEW]

#: Employee (EL-UC-001, 006..010, 012, 013) and Substitute (EL-UC-002).
_EMPLOYEE = [p.P_VIEW, p.P_CREATE, p.P_UPDATE, p.P_WITHDRAW, p.P_SUBSTITUTE, p.P_BALANCE]
#: Unit Head (EL-UC-003, EL-UC-011; BR-EL-016, BR-EL-017).
_UNIT_HEAD = [p.P_REVIEW, p.P_APPROVE, p.P_RESUMPTION]
#: Deputy Registrar (Estt.) (EL-UC-004, EL-UC-011).
_ESTABLISHMENT = [p.P_REVIEW, p.P_RESUMPTION]
#: Registrar / Director (EL-UC-005; BR-EL-018..020).
_SANCTIONING = [p.P_REVIEW, p.P_APPROVE, p.P_RESUMPTION]
#: Leave Administrator (EL-UC-014..016).
_ADMIN = [p.P_POLICY, p.P_CALENDAR, p.P_OFFLINE, p.P_ACCOUNT_VIEW]

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
    "SectionHead_PS": _UNIT_HEAD,
    "SectionHead_IWD": _UNIT_HEAD,
    "SectionHead_RSPC": _UNIT_HEAD,
    "SectionHead_HR": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Registrar": _SANCTIONING,
    "Director": _SANCTIONING,
    "Leave Administrator": _ADMIN,
}

#: The seeded default hierarchy: faculty to the Director, staff to the Registrar.
DEFAULT_HIERARCHY = {
    "unit_heads": {
        "CSE": "HOD (CSE)", "ECE": "HOD (ECE)", "ME": "HOD (ME)",
        "Design": "HOD (Design)", "Natural Science": "HOD (NS)",
        "Liberal Arts": "HOD (Liberal Arts)", "Purchase and Store": "SectionHead_PS",
        "IWD": "SectionHead_IWD",
    },
    "establishment_role": "Deputy Registrar",
    "establishment_categories": ["SCL", "EL", "COL", "VL"],
    "sanctioning": {"faculty": {"default": "Director"},
                    "staff": {"default": "Registrar"}},
    "director_role": "Director",
    "resumption_verifier": "unit_head",
    "sla": {"reminder_hours": None, "escalation_hours": None, "escalate_to": None},
}


def readiness() -> list[str]:
    """Prerequisites seed_modules reports before marking the module active."""
    from django.db.utils import DatabaseError

    try:
        from modules.elm.selectors.config import effective_policy

        if effective_policy() is None:
            return ["no published ELM leave policy — run `manage.py seed_elm_policy`"]
    except DatabaseError:
        return ["ELM tables are missing — run `manage.py migrate`"]
    return []
