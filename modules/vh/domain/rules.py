# Pure Python validation rules for VHMS domain.
from datetime import date

VALID_BILLING_RESPONSIBILITIES = frozenset({"visitor", "indenter", "institute", "project"})
VALID_VISITOR_CATEGORIES = frozenset({"A", "B", "C", "D"})
VALID_ROOM_TYPES = frozenset({"suite", "non_suite"})
VALID_OCCUPANCY_TYPES = frozenset({"single", "double"})
VALID_MEAL_OPTIONS = frozenset({"full_day", "individual", "add_on"})
VALID_INDIVIDUAL_MEALS = frozenset({"breakfast", "lunch", "dinner"})
VALID_ADDONS = frozenset({"tea", "milk"})

VISITOR_CATEGORY_CHOICES = [
    ("A", "Category A"),
    ("B", "Category B"),
    ("C", "Category C"),
    ("D", "Category D"),
]

BILLING_RESPONSIBILITY_CHOICES = [
    ("visitor", "Visitor"),
    ("indenter", "Indenter"),
    ("institute", "Institute"),
    ("project", "Project"),
]

OCCUPANCY_CHOICES = [
    ("single", "Single"),
    ("double", "Double"),
]

ROOM_TYPE_CHOICES = [
    ("suite", "Suite"),
    ("non_suite", "Non-suite"),
]


def validate_billing_responsibility(value: str) -> str:
    # BR-VH-002: Restricts billing responsibility to Visitor, Indenter, Institute, Project.
    val = value.strip().lower()
    if val not in VALID_BILLING_RESPONSIBILITIES:
        msg = f"Invalid billing: '{value}'. Allowed: Visitor, Indenter, Institute, Project."
        raise ValueError(msg)
    return val


def validate_visitor_category(category: str) -> str:
    # BR-VH-019: Category must be A, B, C, or D.
    cat = category.strip().upper()
    if cat not in VALID_VISITOR_CATEGORIES:
        raise ValueError(f"Invalid visitor category: '{category}'. Allowed: A, B, C, D.")
    return cat


def validate_room_type(room_type: str) -> str:
    # BR-VH-015, BR-VH-016: Room type must be suite or non_suite.
    rt = room_type.strip().lower()
    if rt not in VALID_ROOM_TYPES:
        raise ValueError(f"Invalid room type: '{room_type}'. Allowed: suite, non_suite.")
    return rt


def validate_occupancy_type(occupancy: str) -> str:
    # BR-VH-013, BR-VH-014: Occupancy must be single or double.
    occ = occupancy.strip().lower()
    if occ not in VALID_OCCUPANCY_TYPES:
        raise ValueError(f"Invalid occupancy type: '{occupancy}'. Allowed: single, double.")
    return occ


def validate_stay_dates(arrival_date: date, departure_date: date) -> None:
    # Validates arrival and departure date chronology.
    if departure_date < arrival_date:
        raise ValueError("Departure date cannot precede arrival date.")


def validate_meal_selection(
    meal_option: str,
    individual_type: str | None = None,
    add_on_type: str | None = None,
) -> None:
    # BR-VH-029, BR-VH-030: Enforces meal and add-on options.
    opt = meal_option.strip().lower()
    if opt not in VALID_MEAL_OPTIONS:
        msg = f"Invalid meal option: '{meal_option}'. Allowed: full_day, individual, add_on."
        raise ValueError(msg)
    if opt == "individual" and (
        not individual_type or individual_type.strip().lower() not in VALID_INDIVIDUAL_MEALS
    ):
        raise ValueError(
            f"Invalid individual meal: '{individual_type}'. Allowed: breakfast, lunch, dinner."
        )
    if opt == "add_on" and (not add_on_type or add_on_type.strip().lower() not in VALID_ADDONS):
        raise ValueError(f"Invalid add-on option: '{add_on_type}'. Allowed: tea, milk.")


def validate_meal_date_within_stay(
    meal_date: date,
    arrival_date: date,
    departure_date: date,
) -> None:
    # BR-VH-031: Meal bookings must link to the stay duration.
    if not (arrival_date <= meal_date <= departure_date):
        msg = (
            f"Meal date {meal_date} is outside stay duration ({arrival_date} to {departure_date})."
        )
        raise ValueError(msg)
