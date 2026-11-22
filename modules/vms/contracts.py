"""VMS Public Contracts Surface.
Other modules may communicate with VMS ONLY through this file (enforced by .importlinter).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.vms.models.visitors import BlacklistEntry
from modules.vms.models.visits import Visit


@dataclass(frozen=True)
class ActiveVisitorDTO:
    visitor_id: int
    full_name: str
    phone: str
    host_user_id: int
    pass_number: str
    check_in_time: str
    allowed_zones: tuple[str, ...]


@dataclass(frozen=True)
class VisitorClearanceDTO:
    id_number_hash: str
    is_cleared: bool
    is_blacklisted: bool
    active_pass_count: int


def get_active_visitors_on_campus() -> list[ActiveVisitorDTO]:
    """Returns currently on-site visitors."""
    visits = Visit.objects.filter(status="on_site").select_related("visitor")
    return [
        ActiveVisitorDTO(
            visitor_id=v.visitor.id,
            full_name=f"{v.visitor.first_name} {v.visitor.last_name}",
            phone=v.visitor.phone,
            host_user_id=v.host_user_id,
            pass_number=v.pass_number,
            check_in_time=v.check_in_time.isoformat() if v.check_in_time else "",
            allowed_zones=tuple(v.allowed_zones or []),
        )
        for v in visits
    ]


def get_visitor_clearance_status(id_number_hashes: Sequence[str]) -> dict[str, VisitorClearanceDTO]:
    """Returns clearance status for a sequence of visitor ID hashes."""
    hashes = set(id_number_hashes)
    if not hashes:
        return {}

    blacklisted_hashes = set(
        BlacklistEntry.objects.filter(id_number_hash__in=hashes, is_active=True).values_list(
            "id_number_hash", flat=True
        )
    )

    active_visits = Visit.objects.filter(
        visitor__id_number_hash__in=hashes,
        status__in=["requested", "approved", "on_site"],
    ).values_list("visitor__id_number_hash", flat=True)

    pass_counts: dict[str, int] = {}
    for h in active_visits:
        pass_counts[h] = pass_counts.get(h, 0) + 1

    result = {}
    for h in hashes:
        is_bl = h in blacklisted_hashes
        cnt = pass_counts.get(h, 0)
        is_cleared = (not is_bl) and (cnt == 0)
        result[h] = VisitorClearanceDTO(
            id_number_hash=h,
            is_cleared=is_cleared,
            is_blacklisted=is_bl,
            active_pass_count=cnt,
        )
    return result


def is_host_entertaining_visitors(host_user_ids: Sequence[int]) -> dict[int, bool]:
    """Whether hosts currently have active visitors on-site."""
    uids = {int(uid) for uid in host_user_ids if uid is not None}
    if not uids:
        return {}
    active_hosts = set(
        Visit.objects.filter(host_user_id__in=uids, status="on_site").values_list(
            "host_user_id", flat=True
        )
    )
    return {uid: (uid in active_hosts) for uid in uids}
