"""Overlap rules for active leave requests."""
from datetime import date

ACTIVE_STATUSES = {"awaiting_substitute", "substitute_declined", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director", "approved", "cancellation_pending", "resumption_pending"}


def overlaps(start: date, end: date, half: str, category: str, existing) -> bool:
    for item in existing:
        if item.status not in ACTIVE_STATUSES or item.end_date < start or item.start_date > end:
            continue
        if category == "CL" and item.category == "CL" and start == end == item.start_date == item.end_date and half and item.half and half != item.half:
            continue
        return True
    return False
