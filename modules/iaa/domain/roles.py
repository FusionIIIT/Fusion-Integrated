"""Designations IAA grants to, and how an acting role maps to a kind of actor."""
from __future__ import annotations

FINANCE = "iaa_finance_staff"
AUDITOR = "iaa_auditor"
SYSTEM_ADMIN = "iaa_system_admin"
HOD = "iaa_hod"
DEAN = "iaa_dean"
DIRECTOR = "iaa_director"

APPROVERS = frozenset({HOD, DEAN, DIRECTOR})
# An HoD decides only for their own department; Dean and Director are institute-wide.
DEPARTMENT_SCOPED = frozenset({HOD})
RESOLVERS = frozenset({FINANCE, AUDITOR, HOD, DEAN, DIRECTOR})

OWNER = "owner"
FINANCE_ACTOR = "finance"
APPROVER_ACTOR = "approver"
AUDITOR_ACTOR = "auditor"
ADMIN_ACTOR = "admin"
SYSTEM = "system"


def actor_kind(active_role: str | None) -> str:
    if active_role == FINANCE:
        return FINANCE_ACTOR
    if active_role == AUDITOR:
        return AUDITOR_ACTOR
    if active_role == SYSTEM_ADMIN:
        return ADMIN_ACTOR
    if active_role in APPROVERS:
        return APPROVER_ACTOR
    return OWNER
