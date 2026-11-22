"""PHC services: ambulance logging, announcements, and reporting.

AFR-PHC-032, AFR-PHC-033, AFR-PHC-034, AFR-PHC-035.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import Case, DecimalField, F, Sum, Value, When

from core.api.exceptions import BadRequestError
from modules.phc.models import AmbulanceLog, HealthAnnouncement

log = logging.getLogger("fusion.phc.operations")


# ---------------------------------------------------------------------------
# Ambulance  (AFR-PHC-032)
# ---------------------------------------------------------------------------


def log_ambulance_usage(
    *,
    patient_name: str,
    destination: str,
    usage_at: datetime,
    notes: str = "",
    actor_user_id: int,
) -> AmbulanceLog:
    """PHC-UC-11: Record ambulance usage with all required fields."""
    if not patient_name.strip():
        raise BadRequestError("patient_name is required.")
    if not destination.strip():
        raise BadRequestError("destination is required.")
    entry = AmbulanceLog.objects.create(
        patient_name=patient_name.strip(),
        destination=destination.strip(),
        usage_at=usage_at,
        notes=notes,
        recorded_by_user_id=actor_user_id,
    )
    log.info("phc.ambulance.logged entry=%s by=%s", entry.pk, actor_user_id)
    return entry


# ---------------------------------------------------------------------------
# Health Announcements  (AFR-PHC-033)
# ---------------------------------------------------------------------------


def publish_announcement(
    *,
    title: str,
    body: str,
    actor_user_id: int,
) -> HealthAnnouncement:
    """PHC-UC-12: Publish a health advisory to all patients.

    E1: missing content blocks publication.
    """
    if not title.strip():
        raise BadRequestError("title is required for a health announcement.")
    if not body.strip():
        raise BadRequestError("body is required for a health announcement.")
    ann = HealthAnnouncement.objects.create(
        title=title.strip(),
        body=body.strip(),
        is_published=True,
        published_by_user_id=actor_user_id,
    )
    log.info("phc.announcement.published ann=%s by=%s", ann.pk, actor_user_id)
    return ann


# ---------------------------------------------------------------------------
# Reports  (AFR-PHC-034, AFR-PHC-035, PHC-BR-12)
# ---------------------------------------------------------------------------


def generate_report(report_type: str) -> dict:
    """PHC-UC-13: Generate an anonymized administrative report.

    PHC-BR-12: patient-identifiable information is NOT exposed.
    Supported types:
      - "demographics"      → patient visit counts by age-group/gender (no names/IDs)
      - "utilization"       → visits per day/week
      - "inventory"         → current stock levels
    """
    from modules.phc.models import InventoryAudit, InventoryItem, PatientVisit

    if report_type == "demographics":
        from modules.directory import contracts as directory_contracts

        total = PatientVisit.objects.count()
        by_patient = list(
            PatientVisit.objects.values("user_id")
            .annotate(visits=models.Count("id"))
            .order_by("user_id")
        )
        user_details = directory_contracts.get_users([row["user_id"] for row in by_patient])
        groups = {}
        for row in by_patient:
            person = user_details.get(row["user_id"])
            if person is None:
                category = "unclassified"
            elif person.kind == "student":
                category = "student"
            elif person.kind in {"faculty", "staff"}:
                category = "employee"
            else:
                category = "unclassified"
            group = groups.setdefault(category, {"patients": 0, "visits": 0})
            group["patients"] += 1
            group["visits"] += row["visits"]
        return {
            "report_type": "demographics",
            "description": (
                "Aggregate patient and visit counts by patient category. "
                "No patient-identifiable data included."
            ),
            "total_visits": total,
            "patient_groups": [
                {"category": category, **counts} for category, counts in sorted(groups.items())
            ],
        }

    if report_type == "utilization":
        from django.db.models.functions import TruncMonth

        rows = (
            PatientVisit.objects.annotate(month=TruncMonth("visit_date"))
            .values("month")
            .annotate(visits=models.Count("id"))
            .order_by("month")
        )
        return {
            "report_type": "utilization",
            "description": "Visit counts by month. No patient-identifiable data included.",
            "rows": [
                {
                    "month": str(
                        (r["month"].date() if isinstance(r["month"], datetime) else r["month"])
                        or ""
                    ),
                    "visits": r["visits"],
                }
                for r in rows
            ],
        }

    if report_type == "inventory":
        items = list(
            InventoryItem.objects.values("name", "unit", "stock_quantity", "reorder_threshold")
        )
        return {
            "report_type": "inventory",
            "description": "Current inventory stock levels.",
            "items": [
                {
                    "name": i["name"],
                    "unit": i["unit"],
                    "stock_quantity": str(i["stock_quantity"]),
                    "reorder_threshold": str(i["reorder_threshold"]),
                    "is_low_stock": i["stock_quantity"] < i["reorder_threshold"],
                }
                for i in items
            ],
        }

    if report_type == "inventory_consumption":
        rows = (
            InventoryAudit.objects.filter(delta__lt=0)
            .values("item_id", "item__name", "item__unit")
            .annotate(
                quantity_consumed=Sum(
                    Case(
                        When(delta__lt=0, then=-F("delta")),
                        default=Value(Decimal("0")),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
            )
            .order_by("item__name")
        )
        return {
            "report_type": "inventory_consumption",
            "description": "Aggregate stock quantities deducted from inventory audit history.",
            "items": [
                {
                    "item_name": row["item__name"],
                    "unit": row["item__unit"],
                    "quantity_consumed": str(row["quantity_consumed"]),
                }
                for row in rows
            ],
        }

    raise BadRequestError(
        f"Unknown report type {report_type!r}. "
        "Supported: 'demographics', 'utilization', 'inventory', "
        "'inventory_consumption'."
    )
