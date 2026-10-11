"""Cross-module public contract for leave module.
Adheres to Fusion architecture rule:
- Cross-module getters are PLURAL and accept sequences of IDs.
"""
from typing import Sequence, Dict, Any, List
from modules.leave.models import LeaveBalance, LeaveApplication


def get_leave_balances(user_ids: Sequence[str], year: int) -> Dict[str, List[Dict[str, Any]]]:
    """Plural getter for employee leave balances."""
    balances = LeaveBalance.objects.filter(user_id__in=user_ids, year=year)
    result = {uid: [] for uid in user_ids}
    for b in balances:
        result[b.user_id].append({
            "category": b.category,
            "balance": b.balance,
            "year": b.year,
        })
    return result


def get_active_leaves(user_ids: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Plural getter for ongoing / approved leaves."""
    leaves = LeaveApplication.objects.filter(
        applicant_id__in=user_ids,
        status="APPROVED"
    )
    result = {uid: [] for uid in user_ids}
    for lv in leaves:
        result[lv.applicant_id].append({
            "id": lv.id,
            "category": lv.category,
            "start_date": lv.start_date,
            "end_date": lv.end_date,
            "chargeable_days": lv.chargeable_days,
        })
    return result
