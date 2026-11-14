"""OAP Domain Validations.

Pure Python business rule validation functions.
"""

from datetime import date
from typing import Optional

from modules.oap.domain import constants as c


class DomainValidationError(Exception):
    """Raised when domain constraints or business rule invariants are violated."""
    pass


def validate_leave_request(start_date: date, end_date: date, reason: str) -> None:
    if not reason or not reason.strip():
        raise DomainValidationError("Leave reason cannot be empty.")
    if start_date > end_date:
        raise DomainValidationError("Leave start date cannot be after end date.")


def validate_bonafide_request(purpose: str) -> None:
    if not purpose or not purpose.strip():
        raise DomainValidationError("Bonafide certificate purpose cannot be empty.")


def validate_no_dues_clearance(domain: str, status: str, dues_amount: Optional[float] = None) -> None:
    if domain not in c.MANDATORY_NO_DUES_DOMAINS:
        raise DomainValidationError(f"Invalid clearance domain: '{domain}'. Must be one of {c.MANDATORY_NO_DUES_DOMAINS}.")
    if status not in c.CLEARANCE_STATUSES:
        raise DomainValidationError(f"Invalid clearance status: '{status}'. Must be one of {c.CLEARANCE_STATUSES}.")
    if status == c.CLEARANCE_DUES_OUTSTANDING and dues_amount is not None and dues_amount < 0:
        raise DomainValidationError("Outstanding dues amount cannot be negative.")


def validate_assistantship_claim(month: int, year: int, stipend_amount: float, work_summary: str) -> None:
    if month < 1 or month > 12:
        raise DomainValidationError(f"Invalid month: {month}. Must be between 1 and 12.")
    if year < 2000:
        raise DomainValidationError(f"Invalid year: {year}.")
    if stipend_amount < 0:
        raise DomainValidationError("Stipend amount cannot be negative.")
    if not work_summary or not work_summary.strip():
        raise DomainValidationError("Assistantship work summary cannot be empty.")


def validate_seminar_request(title: str, abstract: str) -> None:
    if not title or not title.strip():
        raise DomainValidationError("Seminar title cannot be empty.")
    if not abstract or not abstract.strip():
        raise DomainValidationError("Seminar abstract cannot be empty.")


def validate_seminar_scheduling(scheduled_date: date, scheduled_time: str, venue: str) -> None:
    if not venue or not venue.strip():
        raise DomainValidationError("Seminar venue cannot be empty.")
    if not scheduled_time or not scheduled_time.strip():
        raise DomainValidationError("Seminar scheduled time cannot be empty.")
