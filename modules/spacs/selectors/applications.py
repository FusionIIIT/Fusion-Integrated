"""Application queries and work queue selectors for SPACS.

Enforces:
- CFR-SPACS-006 (Verification work queue)
- CFR-SPACS-008 (Convener decision queue)
- CFR-SPACS-011 (Student status history)
"""
from __future__ import annotations

from django.db.models import QuerySet
from modules.spacs.models import ScholarshipApplication, SpacsTask
from modules.spacs.domain.state_machines import (
    APP_STATUS_SUBMITTED,
    APP_STATUS_RESUBMITTED,
    APP_STATUS_UNDER_VERIFICATION,
    APP_STATUS_VERIFIED_ROUTED,
    APP_STATUS_VERIFICATION_CONCERN,
    APP_STATUS_UNDER_CONVENER_REVIEW,
)


def get_student_applications(user_id: int) -> QuerySet[ScholarshipApplication]:
    """Returns all applications owned by a student."""
    return (
        ScholarshipApplication.objects.filter(user_id=user_id)
        .select_related("policy_version", "policy_version__catalogue_entry")
        .prefetch_related("documents")
        .order_by("-created_at")
    )


def get_assistant_verification_queue() -> QuerySet[ScholarshipApplication]:
    """Returns applications currently awaiting or undergoing assistant verification."""
    return (
        ScholarshipApplication.objects.filter(
            status__in=[
                APP_STATUS_SUBMITTED,
                APP_STATUS_RESUBMITTED,
                APP_STATUS_UNDER_VERIFICATION,
            ]
        )
        .select_related("policy_version", "policy_version__catalogue_entry")
        .prefetch_related("documents")
        .order_by("submitted_at", "created_at")
    )


def get_convener_decision_queue() -> QuerySet[ScholarshipApplication]:
    """Returns applications routed to the Convener for final sanction decision."""
    return (
        ScholarshipApplication.objects.filter(
            status__in=[
                APP_STATUS_VERIFIED_ROUTED,
                APP_STATUS_VERIFICATION_CONCERN,
                APP_STATUS_UNDER_CONVENER_REVIEW,
            ]
        )
        .select_related("policy_version", "policy_version__catalogue_entry")
        .prefetch_related("documents")
        .order_by("verified_at", "submitted_at")
    )


def get_pending_tasks_for_role(role_name: str) -> QuerySet[SpacsTask]:
    """Returns all active, uncompleted SpacsTasks assigned to a role."""
    return (
        SpacsTask.objects.filter(assigned_role=role_name, status="pending")
        .select_related("application", "award_cycle", "policy_version")
        .order_by("due_at", "created_at")
    )
