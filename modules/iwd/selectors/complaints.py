from django.db.models import QuerySet
from rest_framework.exceptions import NotFound

from modules.iwd.models.complaint import Complaint
from modules.iwd.models.estimate import RepairEstimate
from modules.iwd.models.inventory import InventoryItem


def scope_complaints_for_actor(
    user_id: int,
    acting_role: str,
) -> QuerySet[Complaint]:
    role = acting_role.lower()
    if role in ["iwd_admin", "department_head", "director", "auditor", "accounts", "dean"]:
        return Complaint.objects.all()
    if role == "engineer":
        return Complaint.objects.filter(assigned_engineer_id=user_id)
    return Complaint.objects.filter(complainant_user_id=user_id)


def get_scoped_complaint(
    complaint_id: int,
    user_id: int,
    acting_role: str,
) -> Complaint:
    qs = scope_complaints_for_actor(user_id, acting_role)
    try:
        return qs.get(id=complaint_id)
    except Complaint.DoesNotExist as err:
        raise NotFound("Complaint not found.") from err


def scope_estimates_for_complaint(
    complaint_id: int,
) -> QuerySet[RepairEstimate]:
    return RepairEstimate.objects.filter(complaint_id=complaint_id).order_by("-version")


def get_all_inventory() -> QuerySet[InventoryItem]:
    return InventoryItem.objects.all().order_by("item_code")
