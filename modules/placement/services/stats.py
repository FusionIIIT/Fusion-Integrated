"""Reports and statistics (PC-UC-011, PC-UC-012, PC-BR-016).

Staff get operational figures from the live tables; students get anonymised
aggregates from materialised snapshots, so a viral share of the stats page
cannot slow an application deadline. An aggregate over a group of one is not
anonymous, hence the small-cell suppression below.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Max

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


@transaction.atomic
def rebuild(*, season: str) -> int:
    """Recompute every snapshot for a season. Idempotent."""
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        return 0

    records = list(PlacementRecord.objects.filter(policy=policy, is_active=True)
                   .select_related("company"))
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
    """The anonymised figures a student may see (PC-BR-016).

    No names, no per-student rows, and any cell below MIN_CELL suppressed.
    """
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
        "placement_rate": (round(overall.placed * 100 / overall.registered, 1)
                           if overall.registered else None),
        "companies_participated": overall.companies_participated,
        "median_ctc": str(overall.median_ctc) if overall.median_ctc else None,
        "max_ctc": str(overall.max_ctc) if overall.max_ctc else None,
        # Mean CTC and per-discipline splits are absent: they identify outliers.
        "companies": companies,
        "computed_at": overall.computed_at.isoformat(),
    }


def _salary_distribution(records: list[PlacementRecord]) -> list[dict]:
    """PC-AFR-035: Salary package distributions across standard CTC bands.

    Bands: < 6 LPA, 6-10 LPA, 10-15 LPA, 15-25 LPA, 25+ LPA.
    """
    bands = [
        {"band": "< 6 LPA", "min": Decimal("0.0"), "max": Decimal("6.0"), "count": 0},
        {"band": "6-10 LPA", "min": Decimal("6.0"), "max": Decimal("10.0"), "count": 0},
        {"band": "10-15 LPA", "min": Decimal("10.0"), "max": Decimal("15.0"), "count": 0},
        {"band": "15-25 LPA", "min": Decimal("15.0"), "max": Decimal("25.0"), "count": 0},
        {"band": "25+ LPA", "min": Decimal("25.0"), "max": Decimal("9999.0"), "count": 0},
    ]
    for r in records:
        if r.ctc_lpa is None:
            continue
        ctc = r.ctc_lpa
        for b in bands:
            if b["min"] <= ctc < b["max"]:
                b["count"] += 1
                break
    return [{"band": b["band"], "count": b["count"]} for b in bands]


def _multi_season_trends() -> dict:
    """PC-AFR-034 (company participation trend) and PC-AFR-036 (employment trend)."""
    policies = list(PlacementPolicy.objects.all().order_by("season"))
    company_trend = []
    employment_trend = []

    for pol in policies:
        recs = PlacementRecord.objects.filter(policy=pol, is_active=True)
        reg_count = PlacementRegistration.objects.filter(
            policy=pol, status="registered").count()
        placed_count = recs.count()
        companies_count = len(set(recs.values_list("company_id", flat=True)))

        rate = (round(placed_count * 100 / reg_count, 1) if reg_count else 0.0)

        company_trend.append({
            "season": pol.season,
            "companies_count": companies_count,
        })
        employment_trend.append({
            "season": pol.season,
            "registered": reg_count,
            "placed": placed_count,
            "placement_rate": rate,
        })

    return {
        "company_participation_trend": company_trend,
        "employment_trend": employment_trend,
    }


def staff_view(*, season: str) -> dict:
    """Operational figures for the TPO and chairman (PC-UC-011, PC-UC-012,
    PC-AFR-034, PC-AFR-035, PC-AFR-036)."""
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        return {"season": season, "available": False}

    records = list(PlacementRecord.objects.filter(policy=policy, is_active=True)
                   .select_related("company"))
    agg = PlacementRecord.objects.filter(policy=policy, is_active=True).aggregate(
        n=Count("id"), mean=Avg("ctc_lpa"), top=Max("ctc_lpa"))
    ctcs = [r.ctc_lpa for r in records if r.ctc_lpa is not None]

    by_company = list(
        PlacementRecord.objects.filter(policy=policy, is_active=True)
        .values("company__name")
        .annotate(placed=Count("id"), top=Max("ctc_lpa"))
        .order_by("-placed"))
    by_status = dict(
        Application.objects.filter(posting__placement_year=season)
        .values_list("status").annotate(n=Count("id")))

    trends = _multi_season_trends()

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
        "salary_distribution": _salary_distribution(records),
        "by_company": by_company,
        "applications_by_status": by_status,
        "company_participation_trend": trends["company_participation_trend"],
        "employment_trend": trends["employment_trend"],
    }
