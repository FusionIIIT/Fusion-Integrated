"""Selectors for attorney panels, assignments and prosecution queues."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.pms.models import (
    AttorneyAssignment,
    AttorneyPanel,
    PatentabilityAssessment,
    PatentLegalAdvice,
)
from modules.pms.selectors.scoping import get_actor_user_id, is_attorney, is_pcc_admin


def list_attorney_panel() -> QuerySet[AttorneyPanel]:
    """Retrieve all approved attorney panel members."""
    return AttorneyPanel.objects.filter(is_active=True).order_by("current_workload", "name")


def get_attorney_assignments_for_actor(actor) -> QuerySet[AttorneyAssignment]:
    """Retrieve attorney assignments for the current actor."""
    if not is_attorney(actor) and not is_pcc_admin(actor):
        return AttorneyAssignment.objects.none()

    qs = AttorneyAssignment.objects.all().select_related("application")
    if is_pcc_admin(actor):
        return qs

    user_id = get_actor_user_id(actor)
    return qs.filter(attorney_user_id=user_id)


def get_patentability_assessment(application_id: int) -> PatentabilityAssessment | None:
    """Retrieve the patentability assessment for an application."""
    return PatentabilityAssessment.objects.filter(application_id=application_id).first()


def list_application_legal_advice(application_id: int) -> QuerySet[PatentLegalAdvice]:
    """List legal advice recorded for an application."""
    return PatentLegalAdvice.objects.filter(application_id=application_id).order_by("-created_at")
