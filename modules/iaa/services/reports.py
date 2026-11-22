"""Role-scoped, read-only reporting and export (UC-601/602)."""
from __future__ import annotations

from collections.abc import Iterator

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F

from modules.iaa.models import ApprovalStep
from modules.iaa.selectors import scoping
from modules.iaa.services import trail
from modules.iaa.services.authz import require

P_VIEW = "iaa.report.view"
P_EXPORT = "iaa.report.export"
EXPORT_HEADER = ["id", "kind", "status", "department", "request_type", "title", "amount",
                 "financial_year", "submitted_at", "processing_reference"]


def _counts(qs, *fields) -> list[dict]:
    return list(qs.values(*fields).annotate(count=Count("id")).order_by(*fields))


def summary(actor, *, financial_year_id: int | None = None) -> dict:
    require(actor, P_VIEW)
    records = scoping.records_for(actor).exclude(status="draft")
    if financial_year_id is not None:
        records = records.filter(financial_year_id=financial_year_id)
    decided = (ApprovalStep.objects.filter(record__in=records, decided_at__isnull=False)
               .annotate(took=ExpressionWrapper(F("decided_at") - F("assigned_at"),
                                                output_field=DurationField()))
               .values("designation").annotate(avg=Avg("took"), decisions=Count("id"))
               .order_by("designation"))
    return {
        "records": _counts(records, "kind", "status"),
        "approval_turnaround": [
            {"designation": row["designation"], "decisions": row["decisions"],
             "average_hours": round(row["avg"].total_seconds() / 3600, 1)}
            for row in decided],
        "anomalies": _counts(scoping.anomalies_for(actor), "category", "status"),
        "observations": _counts(scoping.observations_for(actor), "status"),
    }


def export_rows(actor) -> Iterator[list]:
    require(actor, P_EXPORT)
    trail.log("configuration", 0, "export_report", actor=actor)
    yield EXPORT_HEADER
    rows = (scoping.records_for(actor).exclude(status="draft").select_related("financial_year")
            .order_by("id"))
    for r in rows.iterator(chunk_size=500):
        yield [r.pk, r.kind, r.status, r.department, r.request_type, r.title, r.amount,
               r.financial_year.code if r.financial_year else "",
               r.submitted_at.isoformat() if r.submitted_at else "", r.processing_reference]
