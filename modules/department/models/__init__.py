from modules.department.models.announcements import Announcement
from modules.department.models.departments import Department, OfficialChange
from modules.department.models.feedback import Feedback, FeedbackNote
from modules.department.models.inventory import InventoryItem, StockMovement, StockRequest
from modules.department.models.notifications import DepartmentNotification
from modules.department.models.resources import LabResource, ProfileRecord, TimetableSlot
from modules.department.models.roles import RoleTenure

__all__ = [
    "Announcement",
    "Department",
    "DepartmentNotification",
    "Feedback",
    "FeedbackNote",
    "InventoryItem",
    "LabResource",
    "OfficialChange",
    "ProfileRecord",
    "RoleTenure",
    "StockMovement",
    "StockRequest",
    "TimetableSlot",
]
