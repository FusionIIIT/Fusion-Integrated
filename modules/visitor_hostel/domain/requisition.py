"""The standardized requisition (UC-VH-001, BR-VH-002, BR-VH-019)."""
from __future__ import annotations

from datetime import date

from modules.visitor_hostel.domain import tariffs

BILLING_RESPONSIBILITIES = ("visitor", "indenter", "institute", "project")
ONLINE = "online"
TELEPHONIC = "telephonic"
WALK_IN = "walk_in"
OFFLINE_SOURCES = (TELEPHONIC, WALK_IN)

#: What an Indenter may ask to change before arrival (UC-VH-006).
MODIFIABLE_FIELDS = ("arrival_date", "arrival_time", "departure_date",
                     "departure_time", "rooms_required", "occupants", "occupancy")


class InvalidRequisition(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def validate(*, category: str, occupancy: str, billing_responsibility: str,
             arrival_date: date, departure_date: date, rooms_required: int,
             occupants: int, today: date) -> None:
    if billing_responsibility not in BILLING_RESPONSIBILITIES:
        raise InvalidRequisition(
            "Billing responsibility must be Visitor, Indenter, Institute or "
            "Project.", "invalid_billing_responsibility")
    if category not in tariffs.CATEGORIES:
        raise InvalidRequisition("Visitor category must be A, B, C or D.",
                                 "invalid_category")
    if occupancy not in tariffs.OCCUPANCIES:
        raise InvalidRequisition("Occupancy must be single or double.",
                                 "invalid_occupancy")
    if arrival_date < today:
        raise InvalidRequisition("The arrival date cannot be in the past.",
                                 "arrival_in_past")
    if departure_date < arrival_date:
        raise InvalidRequisition("The departure date must be on or after arrival.",
                                 "departure_before_arrival")
    if rooms_required < 1:
        raise InvalidRequisition("At least one room is required.", "no_rooms")
    if occupants < 1:
        raise InvalidRequisition("At least one occupant is required.",
                                 "no_occupants")
