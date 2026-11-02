"""Domain entities for Complaint Management System."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ComplaintEntity:
    id: int
    complaint_id: str
    complainant_user_id: int
    category_id: int
    location: str
    description: str
    status: str
    priority: str
    assigned_worker_id: Optional[int]
    assigned_worker_name: str
    is_escalated: bool
    escalation_type: str
    created_at: datetime
    sla_deadline: Optional[datetime]
