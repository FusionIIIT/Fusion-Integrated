"""Reports and statistics (PC-UC-011, PC-UC-012, PC-BR-016)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Exists, Max, OuterRef

from modules.placement.domain import reports
from modules.placement.models import (
    Application,
    PlacementPolicy,
    PlacementRecord,
    PlacementRegistration,
    PlacementStatsSnapshot,
)

#: Below this many placements, a "median CTC" identifies individuals.
MIN_CELL = 5


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _counted_records(policy: PlacementPolicy):
    """Active placements of registered students; a debarred student leaves both sides."""
    registered = PlacementRegistration.objects.filter(
        policy=policy, status="registered").values("user_id")
    return PlacementRecord.objects.filter(policy=policy, is_active=True,
                                          user_id__in=registered)


@transaction.atomic
def rebuild(*, season: str) -> int:
    """Recompute every snapshot for a season. Idempotent."""
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        return 0

    records = list(_counted_records(policy).select_related("company"))
    registered = PlacementRegistration.objects.filter(
        policy=policy, status="registered").count()
    offers = Application.objects.filter(
        posting__placement_year=season,
        status__in=("offer_issued", "offer_accepted")).count()

    rows = [_overall(policy, records, registered, offers)]
    rows += _by_company(policy, records)

    PlacementStatsSnapshot.objects.filter(policy=policy).delete()
    PlacementStatsSnapshot.objects.bulk_create(rows)
    return len(rows)


def _overall(policy, records, registered, offers) -> PlacementStatsSnapshot:
    ctcs = [r.ctc_lpa for r in records if r.ctc_lpa is not None]
    return PlacementStatsSnapshot(
        policy=policy, dimension="overall", dimension_value="",
        registered=registered, placed=len(records), offers=offers,
        companies_participated=len({r.company_id for r in records}),
        median_ctc=_median(ctcs),
        mean_ctc=(sum(ctcs) / len(ctcs)) if ctcs else None,
        max_ctc=max(ctcs) if ctcs else None,
    )


def _by_company(policy, records) -> list[PlacementStatsSnapshot]:
    by: dict[int, list] = {}
    names: dict[int, str] = {}
    for r in records:
        by.setdefault(r.company_id, []).append(r)
        names[r.company_id] = r.company.name

    out = []
    for company_id, rs in by.items():
        ctcs = [r.ctc_lpa for r in rs if r.ctc_lpa is not None]
        out.append(PlacementStatsSnapshot(
            policy=policy, dimension="company",
            dimension_value=names[company_id][:120],
            registered=0, placed=len(rs), offers=len(rs),
            companies_participated=1,
            median_ctc=_median(ctcs),
            mean_ctc=(sum(ctcs) / len(ctcs)) if ctcs else None,
            max_ctc=max(ctcs) if ctcs else None))
    return out


def student_view(*, season: str) -> dict:
    """The anonymised figures a student may see (PC-BR-016)."""
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        return {"season": season, "available": False}

    overall = PlacementStatsSnapshot.objects.filter(
        policy=policy, dimension="overall").first()
    if overall is None or overall.placed < MIN_CELL:
        # Early in a season the totals themselves identify people.
        return {"season": season, "available": False,
                "reason": "Not enough placements yet to publish statistics."}

    companies = [
        {"company": s.dimension_value, "placed": s.placed}
        for s in PlacementStatsSnapshot.objects.filter(
            policy=policy, dimension="company", placed__gte=MIN_CELL)
        .order_by("-placed")[:25]
    ]
    return {
        "season": season,
        "available": True,
        "registered": overall.registered,
        "placed": overall.placed,
        "placement_rate": reports.placement_rate(overall.placed, overall.registered),
        "companies_participated": overall.companies_participated,
        "median_ctc": str(overall.median_ctc) if overall.median_ctc else None,
        "max_ctc": str(overall.max_ctc) if overall.max_ctc else None,
        # Mean CTC and per-discipline splits are absent: they identify outliers.
        "companies": companies,
        "computed_at": overall.computed_at.isoformat(),
    }


def staff_view(*, season: str) -> dict:
    """Operational figures for the TPO and chairman (PC-UC-011, PC-UC-012)."""
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        return {"season": season, "available": False}

    records = _counted_records(policy)
    agg = records.aggregate(n=Count("id"), mean=Avg("ctc_lpa"), top=Max("ctc_lpa"))
    ctcs = [r for r in records.values_list("ctc_lpa", flat=True) if r is not None]

    by_company = list(
        records.values("company__name")
        .annotate(placed=Count("id"), top=Max("ctc_lpa"))
        .order_by("-placed"))
    by_status = dict(
        Application.objects.filter(posting__placement_year=season)
        .values_list("status").annotate(n=Count("id")))

    return {
        "season": season,
        "available": True,
        "registered": PlacementRegistration.objects.filter(
            policy=policy, status="registered").count(),
        "debarred": PlacementRegistration.objects.filter(
            policy=policy, status="debarred").count(),
        "placed": agg["n"] or 0,
        "median_ctc": str(_median(ctcs)) if ctcs else None,
        "mean_ctc": str(round(agg["mean"], 2)) if agg["mean"] else None,
        "max_ctc": str(agg["top"]) if agg["top"] else None,
        "placement_rate": reports.placement_rate(
            agg["n"] or 0, PlacementRegistration.objects.filter(
                policy=policy, status="registered").count()),
        "salary_distribution": reports.salary_distribution(ctcs),
        "by_company": by_company,
        "applications_by_status": by_status,
    }


def trends() -> list[dict]:
    """Company participation and employment across seasons (PC-AFR-034, PC-AFR-036)."""
    seasons = list(PlacementPolicy.objects.values_list("season", flat=True))
    registered = dict(
        PlacementRegistration.objects.filter(status="registered")
        .values_list("policy__season").annotate(n=Count("id")))
    is_registered = PlacementRegistration.objects.filter(
        policy=OuterRef("policy"), user_id=OuterRef("user_id"), status="registered")
    rows = (PlacementRecord.objects.filter(is_active=True).filter(Exists(is_registered))
            .values("policy__season")
            .annotate(placed=Count("id"), companies=Count("company", distinct=True)))
    placed = {r["policy__season"]: r["placed"] for r in rows}
    companies = {r["policy__season"]: r["companies"] for r in rows}
    return [
        {"season": t.season, "registered": t.registered, "placed": t.placed,
         "placement_rate": t.placement_rate,
         "companies_participated": t.companies_participated}
        for t in reports.season_trends(seasons, registered, placed, companies)
    ]
