"""Membership read selectors for Gymkhana."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.gymkhana.models.membership import ClubMembership


def get_membership_by_id(membership_id: int) -> ClubMembership:
    """Return membership by ID or raise NotFound."""
    mem = ClubMembership.objects.select_related("club").filter(id=membership_id).first()
    if not mem:
        raise NotFoundError(f"Membership {membership_id} not found.")
    return mem


def student_has_membership(club_id: int, student_id: int) -> bool:
    """Check if student already applied to this club (BR-GYM-009)."""
    return ClubMembership.objects.filter(club_id=club_id, student_id=student_id).exists()
