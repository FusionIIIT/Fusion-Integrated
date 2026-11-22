from typing import Optional, List
from django.db.models import QuerySet
from ..models import Complaint, Estimate, InventoryItem, FinalBill

def get_complaint(complaint_id: int) -> Optional[Complaint]:
    return Complaint.objects.filter(id=complaint_id).first()

def list_complaints_for_user(user_id: str, role: str) -> QuerySet:
    if role == "employee":
        return Complaint.objects.filter(requester_id=user_id)
    elif role == "engineer":
        return Complaint.objects.filter(assigned_engineer_id=user_id)
    return Complaint.objects.all()

def get_estimate_for_complaint(complaint_id: int) -> Optional[Estimate]:
    return Estimate.objects.filter(complaint_id=complaint_id).first()

def check_item_stock(item_code: str, required_qty: float) -> bool:
    item = InventoryItem.objects.filter(item_code=item_code).first()
    if not item:
        return False
    return item.current_stock >= required_qty

def get_bill_for_complaint(complaint_id: int) -> Optional[FinalBill]:
    return FinalBill.objects.filter(complaint_id=complaint_id).first()
