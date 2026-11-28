"""Plural contract for ELM module (Qwen 14B).
Strictly adheres to plural getter rules.
"""
from typing import Sequence, Dict, Any, List
from modules.leave.models import LeaveAccount, LeaveRequest


def get_leave_accounts(user_ids: Sequence[str], year: int) -> Dict[str, List[Dict[str, Any]]]:
    """Plural getter for leave balances across multiple users."""
    records = LeaveAccount.objects.filter(user_id__in=user_ids, year=year)
    result = {uid: [] for uid in user_ids}
    for r in records:
        result[r.user_id].append({
            "category": r.category,
            "balance": r.balance,
            "employee_type": r.employee_type,
            "year": r.year,
        })
    return result


def get_active_leave_schedules(user_ids: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Plural getter for approved active leave periods."""
    requests = LeaveRequest.objects.filter(applicant_id__in=user_ids, status="APPROVED")
    result = {uid: [] for uid in user_ids}
    for req in requests:
        result[req.applicant_id].append({
            "id": req.id,
            "category": req.category,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "chargeable_days": req.chargeable_days,
            "is_station_leave": req.is_station_leave,
        })
    return result
