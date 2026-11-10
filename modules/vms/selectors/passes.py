"""Pass retrieval for the visitor (VMS-CFR-020, UC-012)."""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import VisitPass, VisitRequest


def visible_pass(visit_request: VisitRequest) -> VisitPass | None:
    """The request's active pass, only while the request is approved."""
    if visit_request.status != VisitRequest.Status.APPROVED:
        return None
    return (visit_request.passes.filter(
        is_active=True, terminated_at__isnull=True, valid_until__gt=timezone.now())
        .prefetch_related("allowed_zones").order_by("-id").first())


def pass_summary(visit_request: VisitRequest) -> dict | None:
    """Pass facts without the credentials (list/detail views)."""
    vp = visit_request.passes.order_by("-id").first()
    if vp is None:
        return None
    return {"id": vp.pk, "pass_type": vp.pass_type, "valid_from": vp.valid_from,
            "valid_until": vp.valid_until, "is_active": vp.is_active}
