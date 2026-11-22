from typing import Final

TECHNICAL: Final[str] = "Technical"
SPORTS: Final[str] = "Sports"
CULTURAL: Final[str] = "Cultural"
CLUB_CATEGORIES: Final[tuple[str, ...]] = (TECHNICAL, SPORTS, CULTURAL)

STATUS_OPEN: Final[str] = "open"
STATUS_CONFIRMED: Final[str] = "confirmed"
CLUB_STATUSES: Final[tuple[str, ...]] = (STATUS_OPEN, STATUS_CONFIRMED)

MEMBERSHIP_STATUSES: Final[tuple[str, ...]] = (STATUS_OPEN, STATUS_CONFIRMED)

BOOKING_SESSION: Final[str] = "session"
BOOKING_EVENT: Final[str] = "event"
BOOKING_TYPES: Final[tuple[str, ...]] = (BOOKING_SESSION, BOOKING_EVENT)

ROLE_COORDINATOR: Final[str] = "coordinator"
ROLE_CO_COORDINATOR: Final[str] = "co_coordinator"
LEADERSHIP_ROLES: Final[tuple[str, ...]] = (ROLE_COORDINATOR, ROLE_CO_COORDINATOR)

CONFIGURED_VENUES: Final[tuple[str, ...]] = (
    "L-101",
    "L-102",
    "CC1",
    "CC2",
    "Hall-1",
    "Sports Ground",
    "Auditorium",
)
