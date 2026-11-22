"""Pure domain business policies and invariants for Hostel Management.

Imports no Django, no DRF, no Celery. Pure Python.
"""


class PolicyViolationError(Exception):
    pass


def validate_room_capacity(current_occupancy: int, room_capacity: int) -> None:
    # BR-HM-010: Room Capacity Limit Enforcement
    if current_occupancy >= room_capacity:
        msg = f"Room capacity limit reached ({room_capacity})."
        raise PolicyViolationError(msg)


def validate_notice_topic(topic: str) -> None:
    # BR-HM-029: Assigned-Hostel Notice Publishing
    valid_topics = {"general", "maintenance", "disciplinary", "event", "emergency"}
    if topic not in valid_topics:
        msg = f"Invalid notice topic '{topic}'. Must be one of {valid_topics}."
        raise PolicyViolationError(msg)


def validate_fine_amount(amount: float) -> None:
    # BR-HM-025: Fine Mandatory Data Fields & positive amount
    if amount <= 0:
        msg = "Fine amount must be greater than zero."
        raise PolicyViolationError(msg)
