"""Contract boundary for the ELM module (ADR-0013: No cross-module Foreign Keys)."""
from decimal import Decimal
from typing import Dict, Any

def get_employee_leave_summary(user_id: str) -> Dict[str, Any]:
    """Public read API exposed to other modules (e.g. Payroll / Attendance)."""
    from .selectors.leave_selectors import get_user_balances
    balances = get_user_balances(user_id)
    return {
        "user_id": user_id,
        "balances": {b.leave_type: float(b.balance) for b in balances},
    }
