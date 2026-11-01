"""Selectors for director review queues and assignments."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.pms.models import DirectorAssignment, DirectorReview
from modules.pms.selectors.scoping import get_actor_user_id, is_director, is_pcc_admin


def get_pending_director_assignments(actor) -> QuerySet[DirectorAssignment]:
    """Retrieve pending review assignments for the active Director."""
    if not is_director(actor) and not is_pcc_admin(actor):
        return DirectorAssignment.objects.none()

    qs = DirectorAssignment.objects.filter(status="assigned").select_related("application")
    if is_pcc_admin(actor):
        return qs

    user_id = get_actor_user_id(actor)
    return qs.filter(director_user_id=user_id)


def get_application_reviews(application_id: int) -> QuerySet[DirectorReview]:
    """Retrieve review history for an application."""
    return DirectorReview.objects.filter(application_id=application_id).order_by("-decided_at")
