from django.db.models import Count, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth

from modules.phc.models import AmbulanceUsage, InventoryMovement, PatientVisit, ReimbursementClaim


def service_utilization_by_month():
    return PatientVisit.objects.annotate(period=TruncMonth("visited_on"))\
        .values("period").annotate(visits=Count("id")).order_by("period")


def inventory_consumption():
    return InventoryMovement.objects.filter(quantity_delta__lt=0)\
        .values("item__name", "item__unit").annotate(
            quantity=-Coalesce(Sum("quantity_delta"), Value(0))).order_by("item__name")


def ambulance_usage_by_month():
    return AmbulanceUsage.objects.annotate(period=TruncMonth("used_at"))\
        .values("period").annotate(count=Count("id")).order_by("period")


def reimbursement_status_counts():
    return ReimbursementClaim.objects.values("state").annotate(
        count=Count("id")).order_by("state")
