"""Role scope, decided in one place.

Enforces BR-PMS-003, BR-PMS-005, BR-PMS-006, BR-PMS-126, BR-PMS-130, and BR-PMS-131.

Every list and detail view starts from a queryset built here. Ownership is
enforced by narrowing the queryset, never by fetching a row and then checking
it — so a row you may not see is a 404, not a 403. A 403 would confirm it
exists, which for confidential patent data is itself a disclosure (BR-PMS-130).

    BR-PMS-003  Applicants may access information only for their own applications
    BR-PMS-005  Directors may access reports/analytics only within authorized scope
    BR-PMS-006  Director workflow-oversight is limited to applications in Director's domain
    BR-PMS-126  A valid PMS role assignment is required before accessing functions
    BR-PMS-130  Confidential patent information is protected by RBAC
    BR-PMS-131  PMS maintains exactly one active PCC_ADMIN oversight role
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.patents.domain.permissions import (
    P_APPLICATION_ASSIGN_DIRECTOR,
    P_APPLICATION_CREATE,
    P_APPLICATION_DECIDE_APPEAL,
    P_APPLICATION_REVIEW,
    P_APPLICATION_UPDATE,
    P_APPLICATION_VIEW_SELF,
    P_APPLICATION_WITHDRAW,
    P_ASSESSMENT_PERFORM,
    P_ATTORNEY_ASSIGN,
    P_ATTORNEY_RESPOND_ASSIGNMENT,
    P_AUDIT_VIEW,
    P_BUDGET_APPROVE,
    P_FILING_RECORD,
    P_MAINTENANCE_DECIDE,
    P_MAINTENANCE_TRACK,
    P_OFFICE_ACTION_RECORD,
    P_OFFICE_ACTION_RESPOND,
    P_PANEL_MANAGE,
    P_TECH_TRANSFER_REVIEW,
)
from modules.patents.models import (
    AppealRecord,
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
    ReviewDecision,
    TechnologyTransferRecord,
)

PCC_ADMIN_ROLE = "pcc_admin"
DIRECTOR_ROLE = "director"
ATTORNEY_ROLE = "attorney"
APPLICANT_ROLES = {"student", "faculty", "staff"}


def _own_id(actor) -> int | None:
    """None means no identity to scope by, resolving to an empty queryset."""
    return getattr(actor, "user_id", None)


def _roles(actor) -> set[str]:
    return {r.lower() for r in getattr(actor, "roles", ())}


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def is_pcc_admin(actor) -> bool:
    """BR-PMS-131: Single active PCC_ADMIN oversight role; sees everything in module."""
    if PCC_ADMIN_ROLE in _roles(actor):
        return True
    return _has(
        actor,
        P_AUDIT_VIEW,
        P_APPLICATION_ASSIGN_DIRECTOR,
        P_ATTORNEY_ASSIGN,
        P_PANEL_MANAGE,
    )


def is_director(actor) -> bool:
    """Evaluates patent applications, appeals, budgets, and renewals in their scope."""
    if DIRECTOR_ROLE in _roles(actor):
        return True
    return _has(
        actor,
        P_APPLICATION_REVIEW,
        P_APPLICATION_DECIDE_APPEAL,
        P_BUDGET_APPROVE,
        P_MAINTENANCE_DECIDE,
        P_TECH_TRANSFER_REVIEW,
    )


def is_attorney(actor) -> bool:
    """Manages patent assessment, filings, and office actions for assigned applications."""
    if ATTORNEY_ROLE in _roles(actor):
        return True
    return _has(
        actor,
        P_ATTORNEY_RESPOND_ASSIGNMENT,
        P_ASSESSMENT_PERFORM,
        P_FILING_RECORD,
        P_OFFICE_ACTION_RECORD,
        P_OFFICE_ACTION_RESPOND,
        P_MAINTENANCE_TRACK,
    )


def is_applicant(actor) -> bool:
    """Applicant creates and tracks their own patent applications."""
    if bool(_roles(actor) & APPLICANT_ROLES):
        return True
    return _has(
        actor,
        P_APPLICATION_VIEW_SELF,
        P_APPLICATION_CREATE,
        P_APPLICATION_UPDATE,
        P_APPLICATION_WITHDRAW,
    )


def has_pms_access(actor) -> bool:
    """BR-PMS-126: A valid PMS role is required before accessing patent-management functions."""
    if _own_id(actor) is None:
        return False
    if getattr(actor, "has_module", None) and not actor.has_module("patents"):
        return False
    return is_pcc_admin(actor) or is_director(actor) or is_attorney(actor) or is_applicant(actor)


# -- Applications -------------------------------------------------------------

def applications_for(actor) -> QuerySet[PatentApplication]:
    """Scoped patent applications queryset.

    BR-PMS-003: Applicants may access information only for their own applications.
    BR-PMS-005 / BR-PMS-006: Director oversight limited to applications in Director's domain.
    BR-PMS-126: Requires valid PMS role assignment.
    BR-PMS-130: Confidential patent info protected by RBAC.
    """
    base = PatentApplication.objects.all()
    if not has_pms_access(actor):
        return base.none()

    if is_pcc_admin(actor):
        return base

    own = _own_id(actor)
    q = Q()

    # Subquery for co-invented applications so no outer DISTINCT is required
    coinvented_ids = CoInventor.objects.filter(user_id=own).values_list("application_id", flat=True)

    # Any user may see applications they authored or co-invented
    q |= Q(user_id=own) | Q(id__in=coinvented_ids)

    # Director sees applications assigned to them
    if is_director(actor):
        q |= Q(assigned_director_id=own)

    # Attorney sees applications assigned to them
    if is_attorney(actor):
        q |= Q(assigned_attorney_id=own)

    return base.filter(q)


# -- Subordinate Collections --------------------------------------------------

def co_inventors_for(actor) -> QuerySet[CoInventor]:
    """Co-inventors visible for applications within actor's scope."""
    return CoInventor.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def documents_for(actor) -> QuerySet[ApplicationDocument]:
    """BR-PMS-130: Documents visible only for applications within actor's scope."""
    return ApplicationDocument.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def review_decisions_for(actor) -> QuerySet[ReviewDecision]:
    """Review decisions visible for applications within actor's scope."""
    return ReviewDecision.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def appeals_for(actor) -> QuerySet[AppealRecord]:
    """Appeals visible for applications within actor's scope."""
    return AppealRecord.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def budget_entries_for(actor) -> QuerySet[PatentBudgetLedger]:
    """Budget ledger records visible for applications within actor's scope."""
    return PatentBudgetLedger.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def office_actions_for(actor) -> QuerySet[OfficeActionRecord]:
    """Office action records visible for applications within actor's scope."""
    return OfficeActionRecord.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def tech_transfers_for(actor) -> QuerySet[TechnologyTransferRecord]:
    """Technology transfer records visible for applications within actor's scope."""
    return TechnologyTransferRecord.objects.select_related("application").filter(
        application__in=applications_for(actor),
    )


def attorney_panel_for(actor) -> QuerySet[AttorneyPanelMember]:
    """UC-PMS-026: Attorney panel members: Admin sees all; attorney sees own; others approved."""
    base = AttorneyPanelMember.objects.all()
    if not has_pms_access(actor):
        return base.none()
    if is_pcc_admin(actor):
        return base
    if is_attorney(actor):
        return base.filter(user_id=_own_id(actor))
    return base.filter(is_approved_panel=True)


def policies_for(actor) -> QuerySet[PatentPolicy]:
    """Patent policy records. Admin sees all; others see active."""
    base = PatentPolicy.objects.all()
    if not has_pms_access(actor):
        return base.none()
    if is_pcc_admin(actor):
        return base
    return base.filter(is_active=True)
