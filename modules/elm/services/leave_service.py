"""
Unified facade for ELM services.
"""

from .calculation import calculate_leave_days, validate_leave_application
from .workflow import (
    apply_for_leave,
    nominate_replacement_substitute,
    respond_substitute_consent,
    review_unit_head,
    sanction_final_decision,
)
from .lifecycle import (
    process_year_end,
    request_cancellation,
    review_cancellation,
    review_duty_resumption,
    submit_duty_resumption,
    withdraw_leave_request,
)

__all__ = [
    "calculate_leave_days",
    "validate_leave_application",
    "apply_for_leave",
    "respond_substitute_consent",
    "nominate_replacement_substitute",
    "review_unit_head",
    "sanction_final_decision",
    "withdraw_leave_request",
    "request_cancellation",
    "review_cancellation",
    "submit_duty_resumption",
    "review_duty_resumption",
    "process_year_end",
]
