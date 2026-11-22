from django.db import transaction
from django.utils import timezone

from modules.psm.domain.validators import ValidationError
from modules.psm.models.discrepancy import (
    DiscrepancyReport,
    DiscrepancyStatus,
)
from modules.psm.models.goods_receipt import GoodsReceiptNote, GRNStatus


def generate_discrepancy_code() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"DISC-{timestamp}"


@transaction.atomic
def raise_discrepancy(
    grn_id: int,
    user_id: int,
    discrepancy_type: str,
    details: str,
) -> DiscrepancyReport:
    """Raises a discrepancy ticket and sets payment on hold (BR-PSM-009)."""
    grn = GoodsReceiptNote.objects.select_for_update().get(pk=grn_id)
    if hasattr(grn, "discrepancy_report"):
        return grn.discrepancy_report

    return DiscrepancyReport.objects.create(
        discrepancy_code=generate_discrepancy_code(),
        grn=grn,
        reported_by_user_id=user_id,
        discrepancy_type=discrepancy_type,
        details=details,
        status=DiscrepancyStatus.OPEN_HOLD_PAYMENT,
    )


@transaction.atomic
def resolve_discrepancy(
    discrepancy_id: int,
    user_id: int,
    resolution_summary: str,
) -> DiscrepancyReport:
    """Resolves discrepancy report, allowing invoice clearance to proceed."""
    if not resolution_summary or not resolution_summary.strip():
        raise ValidationError("Resolution summary is required.")

    report = DiscrepancyReport.objects.select_for_update().get(pk=discrepancy_id)
    report.status = DiscrepancyStatus.RESOLVED
    report.resolution_summary = resolution_summary.strip()
    report.resolved_at = timezone.now()
    report.save(update_fields=["status", "resolution_summary", "resolved_at", "updated_at"])

    # Close GRN
    grn = report.grn
    grn.status = GRNStatus.CLOSED
    grn.save(update_fields=["status", "updated_at"])

    return report
