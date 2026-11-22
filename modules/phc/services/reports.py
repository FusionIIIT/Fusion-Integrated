"""Anonymized administrative reports (PHC-BR-12, AFR-PHC-034..035)."""
from __future__ import annotations

from django.db import transaction

from modules.phc.models import (
    AmbulanceLog,
    InventoryItem,
    Prescription,
    ReimbursementClaim,
    Requisition,
    StockAdjustment,
    Visit,
)
from modules.phc.selectors import scoping
from modules.phc.services import audit

CATEGORIES = ("demographics", "utilization", "inventory")


@transaction.atomic
def generate(actor, category: str) -> dict:
    if category == "demographics":
        report = {
            "category": "demographics",
            "patient_count_by_kind": scoping.patient_counts_by_kind(),
            "note": "counts only; no patient-identifiable information",
        }
    elif category == "utilization":
        report = {
            "category": "utilization",
            "visits": Visit.objects.count(),
            "prescriptions": Prescription.objects.count(),
            "ambulance_logs": AmbulanceLog.objects.count(),
            "claims": ReimbursementClaim.objects.count(),
            "requisitions": Requisition.objects.count(),
            "note": "aggregate counts only",
        }
    elif category == "inventory":
        report = {
            "category": "inventory",
            "stock_adjustments": StockAdjustment.objects.count(),
            "items": InventoryItem.objects.count(),
            "low_stock_items": [
                i.name for i in InventoryItem.objects.all()
                if i.quantity < i.reorder_threshold
            ],
            "note": "item names only; no patient data",
        }
    else:
        report = {
            "category": category,
            "error": "Unknown report category",
            "message": "Choose demographics, utilization or inventory.",
        }
    audit.record(actor, "report.generate", "report", 0, {"category": category})
    return report
