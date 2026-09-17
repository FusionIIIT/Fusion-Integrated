"""What the server tells the shell about this module (ADR-0010)."""
#: `status` is what this module would be once its data exists.
MODULE = {
    "code": "leave", "label": "Leave", "icon": "FaRegCalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "See your own leave"),
    ("leave.request.withdraw", "Withdraw your pending request"),
    ("leave.substitute.respond", "Accept or decline standing in for someone"),
    ("leave.request.review", "Review as unit head and record a recommendation"),
    ("leave.request.route", "Route a recommended request to the competent authority"),
    ("leave.request.sanction", "Take the final decision on a leave request"),
    ("leave.resumption.verify", "Verify a reported resumption of duty"),
    ("leave.balance.view", "See leave balances across employees"),
    ("leave.policy.manage", "Maintain leave policy and entitlement"),
    ("leave.calendar.manage", "Maintain the holiday and restricted-holiday calendar"),
    ("leave.offline.record", "Record leave sanctioned outside the system"),
]

#: Performed by a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave.yearend.run",
    "leave.lifecycle.advance",
    "leave.sla.process",
]

#: Enforced by narrowing the queryset rather than by refusing the request.
SCOPE_PERMISSIONS = ["leave.request.view_self"]

_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.withdraw",
    "leave.substitute.respond",
]
_UNIT_HEAD = [*_EMPLOYEE, "leave.request.review", "leave.balance.view"]
_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.request.route",
    "leave.resumption.verify",
    "leave.balance.view",
]
_AUTHORITY = [*_UNIT_HEAD, "leave.request.sanction", "leave.request.route"]
_ADMIN = [
    *_ESTABLISHMENT,
    "leave.policy.manage",
    "leave.calendar.manage",
    "leave.offline.record",
]

#: Keyed by the designation name as it exists in globals_designation, plus the two basic roles.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,

    # A chair is not an office; review sits with the HODs below.
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
    "dracad": _ESTABLISHMENT,
    "Registrar": _AUTHORITY,
    "Dean Academic": _AUTHORITY,
    "Dean (R&D)": _AUTHORITY,
    "Dean (P&D)": _AUTHORITY,
    "Dean_s": _AUTHORITY,
    "Director": _AUTHORITY,
    "acadadmin": _ADMIN,
}

NAV_ITEMS = [
    # -- employee ---------------------------------------------------------
    {"code": "leave.mine", "label": "My Leave", "icon": "FaRegCalendarCheck",
     "to": "/leave", "required_permission": "leave.request.view_self",
     "sort_order": 10},
    {"code": "leave.apply", "label": "Apply", "icon": "FaPlusCircle",
     "to": "/leave/apply", "required_permission": "leave.request.create",
     "sort_order": 20},
    {"code": "leave.substitute", "label": "Standing In", "icon": "FaUserFriends",
     "to": "/leave/substitute", "required_permission": "leave.substitute.respond",
     "sort_order": 30},

    # -- unit head and above ----------------------------------------------
    {"code": "leave.review", "label": "Review Queue", "icon": "FaClipboardCheck",
     "to": "/leave/review", "required_permission": "leave.request.review",
     "sort_order": 40},
    {"code": "leave.route", "label": "Routing Queue", "icon": "FaShareSquare",
     "to": "/leave/routing", "required_permission": "leave.request.route",
     "sort_order": 50},
    {"code": "leave.sanction", "label": "Sanction Queue", "icon": "FaStamp",
     "to": "/leave/sanction", "required_permission": "leave.request.sanction",
     "sort_order": 60},
    {"code": "leave.resumption", "label": "Resumptions", "icon": "FaUndo",
     "to": "/leave/resumptions", "required_permission": "leave.resumption.verify",
     "sort_order": 70},

    # -- administration ----------------------------------------------------
    {"code": "leave.balances", "label": "Balances", "icon": "FaBalanceScale",
     "to": "/leave/balances", "required_permission": "leave.balance.view",
     "sort_order": 80},
    {"code": "leave.policy", "label": "Policy & Calendar", "icon": "FaCog",
     "to": "/leave/policy", "required_permission": "leave.policy.manage",
     "sort_order": 90},
]


def readiness() -> list[str]:
    """What is still missing before this module can accept an application."""
    from datetime import date

    from modules.directory.models import UserRef
    from modules.leave.models import AuthorityRule, EntryReason, LedgerEntry
    from modules.leave.selectors import policy as policy_selector

    today = date.today()
    missing: list[str] = []

    try:
        effective = policy_selector.effective_policy(today)
    except policy_selector.NoEffectivePolicy:
        return [(
            "no leave policy is published for today — run seed_leave_policy, or "
            "draft and publish one under Policy & Calendar"
        )]

    try:
        policy_selector.effective_calendar(today.year)
    except policy_selector.NoEffectivePolicy:
        missing.append(
            f"no holiday calendar is published for {today.year} — without one no "
            "application can be counted")

    if not AuthorityRule.objects.filter(policy_id=effective.pk).exists():
        missing.append(
            f"policy {effective.version} has no authority rules, so no application "
            "has anywhere to go")

    if not UserRef.objects.filter(kind__in=("faculty", "staff"), is_active=True).exists():
        missing.append("the employee directory is empty — run sync_directory")

    credited = LedgerEntry.objects.filter(
        year=today.year, reason=EntryReason.ANNUAL_CREDIT
    ).exists()
    if not credited:
        missing.append(
            f"nobody has been credited their {today.year} entitlement — run "
            f"leave_credit_year {today.year}, or every application is refused for "
            "insufficient balance")

    return missing
