from decimal import Decimal
from django.db.models import QuerySet, Sum

from modules.pms.models.finance import PatentFinancialTransaction, PaymentStatus


def list_transactions_for_application(app_id: int) -> QuerySet[PatentFinancialTransaction]:
    """Retrieve all append-only financial ledger transactions for an application."""
    return PatentFinancialTransaction.objects.filter(application_id=app_id).order_by("-effective_date", "-created_at")


def compute_application_total_expenditure(app_id: int) -> Decimal:
    """Calculate total disbursed patent expenditure from the append-only ledger."""
    res = (
        PatentFinancialTransaction.objects.filter(
            application_id=app_id,
            payment_status=PaymentStatus.DISBURSED,
        ).aggregate(total=Sum("amount"))
    )
    return res["total"] or Decimal("0.00")
