"""Cross-module public contracts for IWD."""
from typing import Dict, Any, Optional
from modules.iwd.models import Complaint, ComplaintStatus


def get_complaint_status(complaint_id: int) -> Optional[Dict[str, Any]]:
    """Return the status summary of a complaint for cross-module integration."""
    try:
        complaint = Complaint.objects.get(pk=complaint_id)
        return {
            "id": complaint.pk,
            "title": complaint.title,
            "status": complaint.status,
            "complainant_id": complaint.complainant_user_id,
            "assigned_engineer_id": complaint.assigned_engineer_id,
            "is_urgent": complaint.is_urgent,
        }
    except Complaint.DoesNotExist:
        return None

