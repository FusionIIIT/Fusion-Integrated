"""Public contract surface for VMS. Plural by signature (ADR-0004).

ZERO cross-module foreign keys allowed. Return immutable DTOs only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from modules.vms.models import VisitRequest


@dataclass(frozen=True)
class HostVisitorStatusDTO:
    host_id: int
    has_active_visitors: bool
    active_visitor_count: int


@dataclass(frozen=True)
class ActiveVisitorDTO:
    visit_id: int
    visitor_name: str
    visitor_phone: str
    pass_number: str
    check_in_time: datetime | None
    access_zones: list[str]


def get_host_visitor_status(host_ids: Sequence[int]) -> dict[int, HostVisitorStatusDTO]:
    """Return on-site visitor counts for the specified host IDs."""
    ids = {int(h) for h in host_ids if h is not None}
    if not ids:
        return {}

    active_visits = VisitRequest.objects.filter(host_id__in=ids, status="CHECKED_IN").values_list(
        "host_id", flat=True
    )

    counts: dict[int, int] = {}
    for hid in active_visits:
        counts[hid] = counts.get(hid, 0) + 1

    return {
        hid: HostVisitorStatusDTO(
            host_id=hid,
            has_active_visitors=counts.get(hid, 0) > 0,
            active_visitor_count=counts.get(hid, 0),
        )
        for hid in ids
    }


def get_active_visitors_by_hosts(host_ids: Sequence[int]) -> dict[int, list[ActiveVisitorDTO]]:
    """Return detailed DTOs of on-site visitors for each specified host."""
    ids = {int(h) for h in host_ids if h is not None}
    if not ids:
        return {}

    visits = VisitRequest.objects.filter(host_id__in=ids, status="CHECKED_IN").select_related(
        "visitor", "digital_pass"
    )

    results: dict[int, list[ActiveVisitorDTO]] = {hid: [] for hid in ids}
    for v in visits:
        pass_num = v.digital_pass.pass_number if hasattr(v, "digital_pass") else ""
        dto = ActiveVisitorDTO(
            visit_id=v.pk,
            visitor_name=v.visitor.name,
            visitor_phone=v.visitor.phone,
            pass_number=pass_num,
            check_in_time=v.actual_check_in,
            access_zones=v.access_zones or [],
        )
        results[v.host_id].append(dto)

    return results
