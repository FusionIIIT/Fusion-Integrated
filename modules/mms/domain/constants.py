"""Domain constants and enums for Mess Management System (MMS).

Pure Python — no Django, DRF or Celery imports permitted.
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
