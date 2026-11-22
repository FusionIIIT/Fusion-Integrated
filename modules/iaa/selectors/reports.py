"""Reports and dashboard statistics for IAA (IAA-UC-601, IAA-UC-602)."""

from django.db.models import Count, Sum

from modules.iaa.models import (
    Anomaly,
    AuditObservation,
    ExpenseVoucherRequest,
    TAClaim,
)
from modules.iaa.selectors.scoping import (
    scope_anomalies,
    scope_audit_observations,
    scope_requests,
    scope_travel_claims,
)


def get_dashboard_summary(principal):
    requests_qs = scope_requests(ExpenseVoucherRequest.objects.all(), principal)
    travel_qs = scope_travel_claims(TAClaim.objects.all(), principal)
    anomalies_qs = scope_anomalies(Anomaly.objects.all(), principal)
    audit_qs = scope_audit_observations(AuditObservation.objects.all(), principal)

    req_counts = dict(
        requests_qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    travel_counts = dict(
        travel_qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    anomaly_counts = dict(
        anomalies_qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    audit_counts = dict(
        audit_qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )

    total_expense_amount = requests_qs.aggregate(total=Sum("total_amount"))["total"] or 0
    total_travel_amount = travel_qs.aggregate(total=Sum("claimed_amount"))["total"] or 0

    return {
        "requests": {
            "total_count": requests_qs.count(),
            "total_amount": float(total_expense_amount),
            "by_status": req_counts,
        },
        "travel": {
            "total_count": travel_qs.count(),
            "total_amount": float(total_travel_amount),
            "by_status": travel_counts,
        },
        "anomalies": {
            "total_count": anomalies_qs.count(),
            "by_status": anomaly_counts,
        },
        "audit": {
            "total_count": audit_qs.count(),
            "by_status": audit_counts,
        },
    }
