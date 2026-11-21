"""Domain constants and enumerations for the Mess Management System (MMS).

Pure Python with zero framework dependencies.
"""

from enum import StrEnum


class MessRole(StrEnum):
    CARETAKER = "caretaker"
    WARDEN = "warden"


class RegistrationStatus(StrEnum):
    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    REJECTED = "REJECTED"
    DEREGISTERED = "DEREGISTERED"


class RebateStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MealTime(StrEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class DayOfWeek(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class FeedbackCategory(StrEnum):
    FOOD_QUALITY = "FOOD_QUALITY"
    CLEANLINESS = "CLEANLINESS"
    TIMELINESS = "TIMELINESS"
    GENERAL = "GENERAL"
