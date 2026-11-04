"""Principal-based queryset scoping for SPACS.

Enforces:
- ADR-0010 / Data isolation: unauthorized records yield 404 Not Found, never 403.
- CFR-SPACS-017 / AFR-SPACS-051 (Role and Ownership Access Control)
"""
from __future__ import annotations

from typing import Any
from django.db.models import QuerySet
from modules.spacs.models import (
    ScholarshipApplication,
    AwardCycle,
    AwardCandidate,
)


def is_student(principal: Any) -> bool:
    return getattr(principal, "kind", None) == "student"


def is_assistant(principal: Any) -> bool:
    if not principal:
        return False
    return "spacs_assistant" in getattr(principal, "roles", ()) or principal.has_permission("spacs.application.verify")


def is_convener(principal: Any) -> bool:
    if not principal:
        return False
    return "spacs_convener" in getattr(principal, "roles", ()) or principal.has_permission("spacs.application.decide")


def is_committee_member(principal: Any) -> bool:
    if not principal:
        return False
    return "award_eval_committee" in getattr(principal, "roles", ()) or principal.has_permission("spacs.award.evaluate")


def is_auditor(principal: Any) -> bool:
    if not principal:
        return False
    return "spacs_auditor" in getattr(principal, "roles", ()) or principal.has_permission("spacs.audit.view")


def applications_for(principal: Any) -> QuerySet[ScholarshipApplication]:
    """Narrows ScholarshipApplication queryset to records accessible by principal."""
    qs = ScholarshipApplication.objects.select_related("policy_version", "policy_version__catalogue_entry")

    if not principal:
        return qs.none()

    if is_convener(principal) or principal.has_permission("spacs.application.view_all"):
        return qs

    if is_assistant(principal):
        # Assistants see applications undergoing verification or recently verified
        return qs.exclude(status="draft")

    if is_student(principal):
        return qs.filter(user_id=principal.user_id)

    return qs.none()


def award_cycles_for(principal: Any) -> QuerySet[AwardCycle]:
    """Narrows AwardCycle queryset."""
    qs = AwardCycle.objects.select_related("policy_version", "policy_version__catalogue_entry")

    if not principal:
        return qs.none()

    if is_convener(principal) or is_committee_member(principal) or is_auditor(principal):
        return qs

    # Students and general users see only cycles that are officially published (UC-SPACS-020)
    return qs.filter(status="published")


def award_candidates_for(principal: Any, cycle: AwardCycle) -> QuerySet[AwardCandidate]:
    """Narrows AwardCandidate queryset for an award cycle."""
    qs = AwardCandidate.objects.filter(award_cycle=cycle)

    if not principal:
        return qs.none()

    if is_convener(principal) or is_committee_member(principal) or is_auditor(principal):
        return qs

    if cycle.status == "published":
        # Public sees only final approved winners
        return qs.filter(is_final_winner=True)

    return qs.none()
