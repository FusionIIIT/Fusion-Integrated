"""Models for the Department module."""

from modules.dept.models.announcements import Announcement
from modules.dept.models.department import Department
from modules.dept.models.feedback import Feedback
from modules.dept.models.inventory import InventoryItem, StockTransaction
from modules.dept.models.labs import LabResource
from modules.dept.models.official_changes import OfficialDetailChangeRequest
from modules.dept.models.profiles import UserProfileExtension
from modules.dept.models.roles import DepartmentRoleAssignment
from modules.dept.models.stock_requests import StockRequest
from modules.dept.models.timetable import TimetableEntry

__all__ = [
    "Announcement",
    "Department",
    "DepartmentRoleAssignment",
    "Feedback",
    "InventoryItem",
    "LabResource",
    "OfficialDetailChangeRequest",
    "StockRequest",
    "StockTransaction",
    "TimetableEntry",
    "UserProfileExtension",
]
