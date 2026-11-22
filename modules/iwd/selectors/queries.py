from django.db.models import QuerySet

from ..models import Complaint, Estimate, FinalBill, InventoryItem


def get_complaint(complaint_id: int) -> Complaint | None:
    return Complaint.objects.filter(id=complaint_id).first()

def list_complaints_for_user(user_id: str, role: str) -> QuerySet:
    if role == "employee":
        return Complaint.objects.filter(requester_id=user_id)
    if role == "engineer":
        return Complaint.objects.filter(assigned_engineer_id=user_id)
    return Complaint.objects.all()

def get_estimate_for_complaint(complaint_id: int) -> Estimate | None:
    return Estimate.objects.filter(complaint_id=complaint_id).first()

def check_item_stock(item_code: str, required_qty: float) -> bool:
    item = InventoryItem.objects.filter(item_code=item_code).first()
    if not item:
        return False
    return item.current_stock >= required_qty

def get_bill_for_complaint(complaint_id: int) -> FinalBill | None:
    return FinalBill.objects.filter(complaint_id=complaint_id).first()
