"""Selectors for PMS queries and ownership scoping.

Ownership and scope live HERE — once per module, not once per view.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.pms.models import PatentApplication, PmsRoleAssignment


def has_global_application_scope(principal) -> bool:
    """Whether IAM grants institution-wide PMS application visibility."""
    return principal is not None and principal.has_any_permission(
        "pms.workflow.monitor",
        "pms.config.manage",
        "pms.application.assign_director",
        "pms.attorney.assign",
        "pms.panel.manage",
    )


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
        "coinventors",
        "documents",
        "director_reviews",
        "budget",
        "attorney_assignments",
        "office_actions",
        "maintenance_records",
    )

    if principal is None:
        return qs.none()

    # PCC_ADMIN and panel/assignment administrators have institution-wide scope.
    if has_global_application_scope(principal):
        return qs

    # Director domain / assignment scope
    if principal.has_any_permission(
        "pms.application.review",
        "pms.application.review_appeal",
        "pms.budget.review",
        "pms.maintenance.decide",
        "pms.licensing.review",
        "pms.workflow.oversight",
        "pms.report.view",
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
    if principal.has_any_permission(
        "pms.attorney.respond_assignment",
        "pms.patentability.assess",
        "pms.filing.record",
        "pms.office_action.record",
        "pms.office_action.respond",
        "pms.maintenance.manage",
        "pms.advice.record",
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
