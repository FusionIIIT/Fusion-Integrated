"""Read side of visit requests for the visitor and the host (VMS-CFR-021).

Ownership is applied in the queryset, so a request that is not yours simply is
not found (404, never 403).
"""
from __future__ import annotations

from django.db.models import Q

from modules.vms.models import AuditLog, PreAuthorization, VisitRequest


def _filtered(qs, status):
    return qs.filter(status=status) if status else qs


def visitor_requests(visitor_id: int, status: str | None = None):
    """Requests filed by, or made for, this visitor session's person."""
    qs = VisitRequest.objects.filter(
        Q(visitor_id=visitor_id) | Q(created_by_visitor_id=visitor_id))
    return _filtered(qs, status).select_related("visitor").prefetch_related(
        "requested_zones").order_by("-id")


def visitor_request(visitor_id: int, pk: int):
    return visitor_requests(visitor_id).filter(pk=pk).first()


def host_requests(host_user_id: int, status: str | None = None):
    qs = VisitRequest.objects.filter(host_user_id=host_user_id)
    return _filtered(qs, status).select_related("visitor").prefetch_related(
        "requested_zones").order_by("-id")


def history(visit_request: VisitRequest):
    """Status history (CFR-021): the audit rows of the request, oldest first."""
    return list(AuditLog.objects.filter(
        entity_type="visitrequest", entity_id=str(visit_request.pk)
    ).order_by("id").values("action", "created_at", "detail"))


def host_pre_authorizations(host_user_id: int, active_only: bool = False):
    qs = PreAuthorization.objects.filter(host_user_id=host_user_id).select_related(
        "visitor").prefetch_related("zones").order_by("-id")
    if active_only:
        qs = qs.filter(revoked_at__isnull=True)
    return qs
