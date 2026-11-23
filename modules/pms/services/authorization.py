"""Shared actor-to-application checks for PMS service operations."""

from modules.pms.domain.errors import NotPermittedError
from modules.pms.models import AttorneyAssignment, PatentApplication, PmsRoleAssignment


def require_director_scope(application: PatentApplication, director_user_id: int) -> None:
    """Require assignment to the application or an active matching domain scope."""
    if application.assigned_director_user_id == director_user_id:
        return
    has_domain_scope = PmsRoleAssignment.objects.filter(
        user_id=director_user_id,
        role="Director",
        is_active=True,
        domain=application.domain,
    ).exists()
    if not has_domain_scope:
        raise NotPermittedError("This Director is outside the application's authorized scope.")


def require_assigned_attorney(
    application: PatentApplication,
    attorney_user_id: int,
    *,
    require_accepted_assignment: bool = False,
) -> None:
    """Require the actor to match the application's assigned Attorney."""
    if application.assigned_attorney_user_id != attorney_user_id:
        raise NotPermittedError("Only the assigned Attorney may act on this application.")
    if require_accepted_assignment:
        accepted_assignment = AttorneyAssignment.objects.filter(
            application=application,
            attorney_user_id=attorney_user_id,
            status="accepted",
            is_active=True,
        ).exists()
        if not accepted_assignment:
            raise NotPermittedError(
                "The assigned Attorney must have an active accepted assignment."
            )
