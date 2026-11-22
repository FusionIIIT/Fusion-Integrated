"""
Contracts interface for Institute Works Department (IWD).
This is the ONLY file external modules are permitted to import from.
"""
from typing import Optional, Dict, Any
from .models import Complaint, Estimate

def get_complaint_summary(complaint_id: int) -> Optional[Dict[str, Any]]:
    try:
        c = Complaint.objects.get(id=complaint_id)
        return {
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "status": c.status,
            "urgency": c.urgency,
            "requester_id": c.requester_id,
        }
    except Complaint.DoesNotExist:
        return None

def get_complaint_estimate_total(complaint_id: int) -> Optional[float]:
    try:
        e = Estimate.objects.get(complaint_id=complaint_id)
        return float(e.total_cost)
    except Estimate.DoesNotExist:
        return None
