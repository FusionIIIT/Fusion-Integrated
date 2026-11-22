"""Aggregated, anonymised report data (PHC-UC-13, PHC-BR-12); no row here names a patient."""
from __future__ import annotations

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from modules.directory import contracts as directory
from modules.phc.domain.reports import ReportRequest, anonymised_counts, suppress
from modules.phc.models import PatientVisit, ReimbursementClaim, StockAdjustment


def _visits(req: ReportRequest):
    return PatientVisit.objects.filter(visit_date__gte=req.start, visit_date__lte=req.end)


def demographics(req: ReportRequest) -> dict:
    patient_ids = list(_visits(req).values_list("patient_user_id", flat=True).distinct())
    people = directory.get_users(patient_ids)
    kinds = [people[i].kind if i in people else "unknown" for i in patient_ids]
    return {"distinct_patients": suppress(len(patient_ids)),
            "patients_by_kind": anonymised_counts(kinds)}


def utilization(req: ReportRequest) -> dict:
    by_month = (_visits(req).annotate(month=TruncMonth("visit_date")).values("month")
                .annotate(visits=Count("id")).order_by("month"))
    claims = (ReimbursementClaim.objects
              .filter(submitted_at__date__gte=req.start, submitted_at__date__lte=req.end)
              .values("status").annotate(n=Count("id")).order_by("status"))
    return {
        "visits_by_month": [{"month": row["month"].strftime("%Y-%m"),
                             "visits": suppress(row["visits"])} for row in by_month],
        "claims_by_status": {row["status"]: suppress(row["n"]) for row in claims},
    }


def inventory_consumption(req: ReportRequest) -> dict:
    rows = (StockAdjustment.objects
            .filter(delta__lt=0, created_at__date__gte=req.start,
                    created_at__date__lte=req.end)
            .values("item__name", "item__unit").annotate(consumed=Sum("delta"))
            .order_by("item__name"))
    return {"consumption": [{"item": row["item__name"], "unit": row["item__unit"],
                             "quantity": str(-row["consumed"])} for row in rows]}


BUILDERS = {
    "demographics": demographics,
    "utilization": utilization,
    "inventory": inventory_consumption,
}


def build(req: ReportRequest) -> dict:
    return {"category": req.category, "start": req.start.isoformat(),
            "end": req.end.isoformat(), "data": BUILDERS[req.category](req)}
