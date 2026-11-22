"""MMS domain tables, split by aggregate."""

from modules.mms.models.announcement import Announcement
from modules.mms.models.deregistration import Deregistration
from modules.mms.models.feedback import Feedback
from modules.mms.models.menu_item import MenuItem
from modules.mms.models.monthly_bill import MonthlyBill
from modules.mms.models.notification_outbox import NotificationOutbox
from modules.mms.models.rebate_request import RebateRequest
from modules.mms.models.registration import Registration
from modules.mms.models.registration_window import RegistrationWindow
from modules.mms.models.role_assignment import RoleAssignment
from modules.mms.models.special_food_charge import SpecialFoodCharge
from modules.mms.models.special_food_policy import SpecialFoodPolicy
from modules.mms.models.special_food_request import SpecialFoodRequest
from modules.mms.models.special_food_transition import SpecialFoodTransition
from modules.mms.models.vacation_response import VacationResponse
from modules.mms.models.vacation_survey import VacationSurvey

__all__ = [
    "Announcement",
    "Deregistration",
    "Feedback",
    "MenuItem",
    "MonthlyBill",
    "NotificationOutbox",
    "RebateRequest",
    "Registration",
    "RegistrationWindow",
    "RoleAssignment",
    "SpecialFoodCharge",
    "SpecialFoodPolicy",
    "SpecialFoodRequest",
    "SpecialFoodTransition",
    "VacationResponse",
    "VacationSurvey",
]
