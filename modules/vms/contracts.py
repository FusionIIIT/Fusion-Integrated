"""vms's public surface for other modules. Plural by signature."""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VisitStatusDTO:
    user_id: int
    pending_requests: int
    visitors_on_site: int


@dataclass(frozen=True)
class HostelVisitLogDTO:
    """One visitor-log event in a hostel-area zone. Deliberately carries no phone, email or
    identity-document number: Hostel Management gets what it needs to log the visit."""
    log_id: int
    event: str
    zone_id: int
    zone_name: str
    occurred_at: datetime
    pass_id: int
    visitor_name: str
    host_user_id: int


def get_visit_status(user_ids: Sequence[int]) -> dict[int, VisitStatusDTO]:
    """Per-host visit counts, one entry for every requested id (zero when none).

    ``pending_requests`` are requests waiting for that host's decision; ``visitors_on_site``
    are that host's guests currently on campus. Two queries however many hosts are asked for.
    """
    from modules.vms.models import VisitRequest
    from modules.vms.selectors import roster

    ids = sorted({int(u) for u in user_ids})
    if not ids:
        return {}
    pending = Counter(VisitRequest.objects
                      .filter(host_user_id__in=ids, status=VisitRequest.Status.PENDING)
                      .values_list("host_user_id", flat=True))
    on_site = Counter(roster.on_site()
                      .filter(visit_request__host_user_id__in=ids)
                      .values_list("visit_request__host_user_id", flat=True))
    return {u: VisitStatusDTO(user_id=u, pending_requests=pending[u],
                              visitors_on_site=on_site[u]) for u in ids}


def get_hostel_visit_log(*, after_id: int = 0, limit: int = 500) -> list[HostelVisitLogDTO]:
    """Visitor-log events in the hostel-area zones an Admin has scoped in, oldest first.

    Empty unless the ``hostel_management`` integration is enabled and has ``zone_ids``
    (AFR-225, UC-020 step 4: "available to Hostel Management as explicitly scoped"). Page
    with ``after_id`` (the last ``log_id`` seen); ``limit`` is capped at 1000.
    """
    from modules.vms.models import VisitLog
    from modules.vms.services import integration

    zone_ids = integration.hostel_scope()
    if not zone_ids:
        return []
    rows = (VisitLog.objects
            .filter(zone_id__in=zone_ids, pk__gt=max(int(after_id), 0))
            .select_related("zone", "visit_pass__visit_request__visitor")
            .order_by("pk")[:max(1, min(int(limit), 1000))])
    return [HostelVisitLogDTO(
        log_id=r.pk, event=r.event, zone_id=r.zone_id, zone_name=r.zone.name,
        occurred_at=r.created_at, pass_id=r.visit_pass_id,
        visitor_name=r.visit_pass.visit_request.visitor.full_name,
        host_user_id=r.visit_pass.visit_request.host_user_id) for r in rows]
