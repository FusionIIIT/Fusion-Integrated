"""Administrative reporting service with anonymization (CFR-PHC-010, AFR-PHC-034, 035; PHC-BR-12)."""
from typing import Any
from django.db.models import Count, Sum

from modules.directory.contracts import get_users
from modules.phc.models.inventory import InventoryItem, InventoryStockAdjustment
from modules.phc.models.patient_records import PatientVisit
from modules.phc.models.reimbursement import ReimbursementClaim


def generate_administrative_report(report_type: str) -> dict[str, Any]:
    """Generates anonymized administrative report data (BR-12).

    Never exposes individual patient names or roll numbers in reporting output.
    """
    if report_type == "demographics":
        # Aggregate visits by patient kind (student vs faculty vs staff) and discipline
        visits = PatientVisit.objects.all()
        user_ids = list(visits.values_list("patient_user_id", flat=True).distinct())
        users_map = get_users(user_ids)

        kind_counts: dict[str, int] = {}
        discipline_counts: dict[str, int] = {}
        for uid in user_ids:
            u = users_map.get(uid)
            if u:
                kind_counts[u.kind] = kind_counts.get(u.kind, 0) + 1
                if u.discipline:
                    discipline_counts[u.discipline] = discipline_counts.get(u.discipline, 0) + 1

        return {
            "report_type": "demographics",
            "total_unique_patients": len(user_ids),
            "breakdown_by_category": kind_counts,
            "breakdown_by_discipline": discipline_counts,
            "anonymized": True,
        }

    elif report_type == "utilization":
        # Aggregate visits by doctor and by month
        doctor_visits = (
            PatientVisit.objects.values("doctor__name", "doctor__specialization")
            .annotate(visit_count=Count("id"))
            .order_by("-visit_count")
        )
        total_visits = PatientVisit.objects.count()
        total_claims = ReimbursementClaim.objects.count()

        status_breakdown = (
            ReimbursementClaim.objects.values("status")
            .annotate(claim_count=Count("id"))
        )

        return {
            "report_type": "utilization",
            "total_consultations": total_visits,
            "consultations_by_doctor": [
                {
                    "doctor": r["doctor__name"] or "General / Unassigned",
                    "specialization": r["doctor__specialization"] or "General",
                    "count": r["visit_count"],
                }
                for r in doctor_visits
            ],
            "total_reimbursement_claims": total_claims,
            "claim_status_breakdown": {
                r["status"]: r["claim_count"] for r in status_breakdown
            },
            "anonymized": True,
        }

    elif report_type == "inventory":
        # Stock consumption and threshold status
        items = InventoryItem.objects.all()
        total_items = items.count()
        low_stock_items = [
            {"code": i.item_code, "name": i.name, "stock": i.stock_level, "threshold": i.reorder_threshold, "unit": i.unit}
            for i in items if i.stock_level < i.reorder_threshold
        ]

        adjustments = (
            InventoryStockAdjustment.objects.values("item__name", "adjustment_type")
            .annotate(total_quantity=Sum("quantity"), count=Count("id"))
        )

        return {
            "report_type": "inventory",
            "total_catalog_items": total_items,
            "low_stock_alerts_count": len(low_stock_items),
            "low_stock_items": low_stock_items,
            "consumption_summary": list(adjustments),
            "anonymized": True,
        }

    else:
        raise ValueError(f"Unknown report type '{report_type}'. Supported: demographics, utilization, inventory.")
