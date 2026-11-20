"""Selectors for PMS queries and ownership scoping.

Ownership and scope live HERE — once per module, not once per view.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.pms.models import PatentApplication, PmsRoleAssignment


def visible_applications(principal) -> QuerySet[PatentApplication]:
    """Return applications visible to the caller based on their role and permissions.

    - PCC_ADMIN sees all applications across the institution (BR-PMS-003).
    - Director sees applications in an active PMS domain assignment or assigned to them
      (BR-PMS-005, BR-PMS-006). If no domain is configured, scope is assignment-only.
    - Attorney sees only active offered/accepted assignments.
    - Applicant sees only applications where they are the primary applicant or a
      co-inventor (BR-PMS-003).
    """
    qs = PatentApplication.objects.prefetch_related(
        "coinventors", "documents", "director_reviews", "budget", "attorney_assignments"
    )

    if principal is None:
        return qs.none()

    # PCC_ADMIN oversight
    if principal.has_permission("pms.workflow.monitor") or principal.has_permission(
        "pms.config.manage"
    ):
        return qs

    # Director domain / assignment scope
    if principal.has_permission("pms.application.review") or principal.has_permission(
        "pms.workflow.oversight"
    ):
        domains = PmsRoleAssignment.objects.filter(
            user_id=principal.user_id,
            role="Director",
            is_active=True,
        ).exclude(domain="").values_list("domain", flat=True)
        director_scope = Q(assigned_director_user_id=principal.user_id)
        if domains:
            director_scope |= Q(domain__in=domains)
        return qs.filter(director_scope).distinct()

    # Attorney scope
    if principal.has_permission("pms.filing.record") or principal.has_permission(
        "pms.patentability.assess"
    ):
        return qs.filter(
            attorney_assignments__attorney_user_id=principal.user_id,
            attorney_assignments__is_active=True,
            attorney_assignments__status__in=("offered", "accepted"),
        ).distinct()

    # Default: Applicant (personal scope only)
    return qs.filter(
        Q(applicant_user_id=principal.user_id) | Q(coinventors__user_id=principal.user_id)
    ).distinct()
