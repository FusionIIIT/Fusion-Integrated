"""Selectors for IWD complaints.

Enforces scope and ownership in one place (ADR-0010, PC-BR-010 precedent).
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.iwd.domain.state_machine import IWDState
from modules.iwd.models import Complaint

ACTIVE_WORKLOAD_STATES: tuple[str, ...] = (
    IWDState.ASSIGNED.value,
    IWDState.ASSESSED.value,
    IWDState.LOW_COST_REVIEW_PENDING.value,
    IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value,
    IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value,
    IWDState.DIRECTOR_REVIEW_PENDING_MID.value,
    IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value,
    IWDState.ESTIMATE_APPROVED.value,
    IWDState.BIDDING_AUTHORIZED.value,
    IWDState.VENDOR_SELECTED.value,
    IWDState.PROCUREMENT_NEEDED_LOW.value,
    IWDState.PROCUREMENT_NEEDED_MID.value,
    IWDState.MATERIALS_AVAILABLE.value,
    IWDState.MATERIALS_ISSUED.value,
    IWDState.READY_FOR_EXECUTION.value,
    IWDState.VERIFICATION_PENDING.value,
    IWDState.REWORK_REQUIRED.value,
    IWDState.AUDIT_PENDING.value,
    IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING.value,
    IWDState.ACCOUNTS_SETTLEMENT_PENDING.value,
    IWDState.URGENT_REVIEW_PENDING.value,
    IWDState.URGENT_PRIORITY_ACTIVE.value,
)

# Authoritative administrative & supervisory oversight roles for campus maintenance.
# Does not include auditor, accounts_officer, or unverified dean authority.
COMPLAINT_OVERSIGHT_ROLES: tuple[str, ...] = (
    "iwd_admin",
    "Department Head",
    "Director",
)


def visible_complaints(principal) -> QuerySet[Complaint]:
    """Return the complaints visible to the given authenticated principal.

    - Executive/administrative oversight roles (iwd_admin, Department Head, Director):
      see all complaints across the institute.
    - Assigned Engineers: see complaints assigned to them (AFR-IWD-009).
    - Complainants: see complaints submitted by them (AFR-IWD-008).
    - Unauthenticated, unauthorized, or other operational roles: empty queryset.
    """
    if principal is None:
        return Complaint.objects.none()

    # 1. Executive and administrative oversight roles see the full complaint queue
    if principal.active_role in COMPLAINT_OVERSIGHT_ROLES:
        return Complaint.objects.all()

    # 2. Engineer scoping: sees assigned complaints
    is_engineer = (
        principal.active_role == "iwd_engineer"
        or principal.has_permission("iwd.complaint.assess")
    )
    if is_engineer:
        return Complaint.objects.filter(assigned_engineer_id=principal.user_id)

    # 3. Complainant scoping: sees own complaints
    can_view_self = (
        principal.has_permission("iwd.complaint.view_self")
        or principal.has_permission("iwd.complaint.create")
    )
    if can_view_self:
        return Complaint.objects.filter(user_id=principal.user_id)

    return Complaint.objects.none()


def get_complaint_for_user(complaint_id: int, principal) -> Complaint | None:
    """Fetch a single complaint within the caller's authorized scope."""
    return visible_complaints(principal).filter(pk=complaint_id).first()


def get_active_workload(engineer_id: int) -> int:
    """Calculate the active workload count for a specific engineer."""
    return Complaint.objects.filter(
        assigned_engineer_id=engineer_id,
        status__in=ACTIVE_WORKLOAD_STATES,
    ).count()


def get_unassigned_complaints(principal) -> QuerySet[Complaint]:
    """Retrieve unassigned complaints in SUBMITTED state for admin review."""
    return visible_complaints(principal).filter(
        status=IWDState.SUBMITTED.value,
        assigned_engineer_id__isnull=True,
    )

