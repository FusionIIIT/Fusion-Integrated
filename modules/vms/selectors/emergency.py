"""Read-only selectors for emergency muster rosters."""

from __future__ import annotations

from django.db.models import Count, QuerySet

from modules.vms.models import EmergencyMusterRoster


def get_latest_muster_roster() -> QuerySet[EmergencyMusterRoster]:
    latest = EmergencyMusterRoster.objects.order_by("-initiated_at").first()
    if not latest:
        return EmergencyMusterRoster.objects.none()
    return (
        EmergencyMusterRoster.objects.filter(muster_id=latest.muster_id)
        .select_related("visitor", "pass_record")
        .order_by("accountability_status", "visitor__name")
    )


def get_muster_summary(muster_id: str) -> dict[str, int]:
    qs = EmergencyMusterRoster.objects.filter(muster_id=muster_id)
    total = qs.count()
    counts = qs.values("accountability_status").annotate(count=Count("id"))
    res = {"total": total, "accounted": 0, "unaccounted": 0}
    for item in counts:
        if item["accountability_status"] == "ACCOUNTED":
            res["accounted"] = item["count"]
        elif item["accountability_status"] == "UNACCOUNTED":
            res["unaccounted"] = item["count"]
    return res
