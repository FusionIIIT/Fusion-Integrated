"""Role-based scoping for RSPC queries.

In compliance with Step 2.5 of new-module-prompt.md:
Querysets are strictly narrowed by the acting principal's role. An item out of scope
returns 404 (NotFoundError), never 403, preventing existence disclosure.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.rspc.models import Project, Proposal


def get_principal(request):
    return getattr(request, "principal", None)


def is_admin_or_dean(request) -> bool:
    """Check if the acting user has institute-wide administrative oversight."""
    p = get_principal(request)
    if not p:
        return False
    roles = set(p.roles)
    if p.active_role:
        roles.add(p.active_role)
    admin_roles = {"admin", "administrator", "Dean (RSPC)", "Dean (R&D)", "Director"}
    return bool(roles & admin_roles)


def get_user_id(request) -> int:
    """Extract authenticated plain integer user_id."""
    p = get_principal(request)
    if not p:
        return 0
    return int(p.user_id)


def is_hod(request) -> bool:
    """Check if the acting user holds a Head of Department role."""
    p = get_principal(request)
    if not p:
        return False
    roles = set(p.roles)
    if p.active_role:
        roles.add(p.active_role)
    return "Head of Department" in roles or "hod" in roles


def scope_proposals(request) -> QuerySet[Proposal]:
    """Narrow proposals queryset to what the current user is permitted to view."""
    qs = Proposal.objects.all()
    if is_admin_or_dean(request):
        return qs
    user_id = get_user_id(request)
    if is_hod(request):
        return qs.filter(Q(user_id=user_id) | Q(status__in=["submitted_hod", "endorsed_hod"]))
    return qs.filter(user_id=user_id)


def scope_projects(request) -> QuerySet[Project]:
    """Narrow projects queryset to what the current user is permitted to view."""
    qs = Project.objects.all()
    if is_admin_or_dean(request):
        return qs
    user_id = get_user_id(request)
    if is_hod(request):
        return qs.filter(
            Q(user_id=user_id) | Q(co_pis__user_id=user_id) | Q(status__in=["sanctioned", "active"])
        ).distinct()
    return qs.filter(Q(user_id=user_id) | Q(co_pis__user_id=user_id)).distinct()


def get_proposal_or_404(request, proposal_id: int) -> Proposal:
    """Fetch a scoped proposal or raise 404."""
    try:
        return scope_proposals(request).get(pk=proposal_id)
    except Proposal.DoesNotExist as err:
        raise NotFoundError(f"Proposal#{proposal_id} not found.") from err


def get_project_or_404(request, project_id: int) -> Project:
    """Fetch a scoped project or raise 404."""
    try:
        return scope_projects(request).get(pk=project_id)
    except Project.DoesNotExist as err:
        raise NotFoundError(f"Project#{project_id} not found.") from err
