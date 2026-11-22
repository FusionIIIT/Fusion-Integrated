"""Pure Python state machine, constants, and business rule guards for MMS.

Deliberately has zero Django or DRF dependencies.
"""
from datetime import date, timedelta
from decimal import Decimal

# Role constants (BR-MMS-002..007)
ROLE_CARETAKER = "mess_caretaker"
ROLE_WARDEN = "mess_warden"
ALLOWED_OPERATIONAL_ROLES = {ROLE_CARETAKER, ROLE_WARDEN}

# Registration States (CFR-MMS-004, BW-MMS-01..02, CW-MMS-01)
REG_SUBMITTED = "submitted"
REG_APPROVED = "approved"
REG_REJECTED = "rejected"
REG_STATUSES = {REG_SUBMITTED, REG_APPROVED, REG_REJECTED}

# Deregistration States (CFR-MMS-005, BW-MMS-03..04, CW-MMS-02)
DEREG_SUBMITTED = "submitted"
DEREG_APPROVED = "approved"
DEREG_REJECTED = "rejected"
DEREG_STATUSES = {DEREG_SUBMITTED, DEREG_APPROVED, DEREG_REJECTED}

# Rebate States (CFR-MMS-011, BW-MMS-05..07, CW-MMS-03)
REBATE_SUBMITTED = "submitted"
REBATE_APPROVED = "approved"
REBATE_REJECTED = "rejected"
REBATE_STATUSES = {REBATE_SUBMITTED, REBATE_APPROVED, REBATE_REJECTED}

# Special Food States (CFR-MMS-013, BR-MMS-031, BW-MMS-11..15, CW-MMS-05)
SPECIAL_FOOD_REQUESTED = "requested"
SPECIAL_FOOD_APPROVED = "approved"
SPECIAL_FOOD_REJECTED = "rejected"
SPECIAL_FOOD_SERVED = "served"
SPECIAL_FOOD_CANCELLED = "cancelled"
SPECIAL_FOOD_STATUSES = {
    SPECIAL_FOOD_REQUESTED,
    SPECIAL_FOOD_APPROVED,
    SPECIAL_FOOD_REJECTED,
    SPECIAL_FOOD_SERVED,
    SPECIAL_FOOD_CANCELLED,
}

# Bill States (CFR-MMS-009, BW-MMS-16)
BILL_DRAFT = "draft"
BILL_GENERATED = "generated"
BILL_PUBLISHED = "published"
BILL_STATUSES = {BILL_DRAFT, BILL_GENERATED, BILL_PUBLISHED}

# Window Statuses
WINDOW_OPEN = "open"
WINDOW_CLOSED = "closed"

# Survey Statuses
SURVEY_OPEN = "open"
SURVEY_CLOSED = "closed"

# Days of week
DAYS_OF_WEEK = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}

# Meal types
MEAL_TYPES = {"breakfast", "lunch", "dinner"}


class InvalidTransition(Exception):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(f"Cannot transition from {from_state!r} to {to_state!r}.")
        self.from_state = from_state
        self.to_state = to_state


class RuleViolation(Exception):
    def __init__(self, rule_id: str, message: str):
        super().__init__(f"[{rule_id}] {message}")
        self.rule_id = rule_id
        self.message = message


def validate_rebate_duration(start_date: date, end_date: date) -> int:
    """BR-MMS-021: Rebate duration must be at least three days (inclusive)."""
    if end_date < start_date:
        raise RuleViolation("BR-MMS-021", "Rebate end date cannot precede start date.")
    duration = (end_date - start_date).days + 1
    if duration < 3:
        raise RuleViolation(
            "BR-MMS-021",
            f"Rebate duration of {duration} day(s) is invalid. Minimum duration is 3 days.",
        )
    return duration


def validate_rebate_lead_time(start_date: date, submission_date: date) -> None:
    """BR-MMS-022: Rebate request must be submitted at least one calendar day before start date."""
    if (start_date - submission_date).days < 1:
        raise RuleViolation(
            "BR-MMS-022",
            "Rebate request must be submitted at least one calendar day before the rebate start date.",
        )


def validate_special_food_lead_time(requested_date: date, submission_date: date) -> None:
    """BR-MMS-028: Special food request must be submitted at least one calendar day before requested date."""
    if (requested_date - submission_date).days < 1:
        raise RuleViolation(
            "BR-MMS-028",
            "Special food request must be submitted at least one calendar day before requested date.",
        )


def calculate_deregistration_effective_date(decision_date: date) -> date:
    """BR-MMS-013: Approved deregistration takes effect from the next calendar day."""
    return decision_date + timedelta(days=1)


def calculate_bill_total(
    base_amount: Decimal,
    special_food_amount: Decimal,
    rebate_discount: Decimal,
) -> Decimal:
    """BR-MMS-017: Bill = base mess fee + special food charges - approved rebate deductions."""
    total = base_amount + special_food_amount - rebate_discount
    return max(Decimal("0.00"), total)


def validate_special_food_transition(current_status: str, new_status: str) -> str:
    """BR-MMS-031: Allowed transitions:

    requested -> approved | rejected
    approved -> served | cancelled
    """
    if current_status == SPECIAL_FOOD_REQUESTED:
        if new_status in {SPECIAL_FOOD_APPROVED, SPECIAL_FOOD_REJECTED}:
            return new_status
    elif current_status == SPECIAL_FOOD_APPROVED:
        if new_status in {SPECIAL_FOOD_SERVED, SPECIAL_FOOD_CANCELLED}:
            return new_status
    raise InvalidTransition(current_status, new_status)
