"""Department domain tables, split by aggregate."""
from modules.department.models.announcements import Announcement
from modules.department.models.departments import Department
from modules.department.models.feedback import Feedback
from modules.department.models.inventory import InventoryItem, StockMovement, StockRequest
from modules.department.models.notifications import DepartmentNotification
from modules.department.models.profiles import (
    CourseRoster,
    DepartmentProfile,
    OfficialChangeProposal,
)
from modules.department.models.role_assignments import DepartmentRoleAssignment
from modules.department.models.timetable import AcademicProgram, LabResource, TimetableSlot

__all__ = [
    "AcademicProgram",
    "Announcement",
    "CourseRoster",
    "Department",
    "DepartmentNotification",
    "DepartmentProfile",
    "DepartmentRoleAssignment",
    "Feedback",
    "InventoryItem",
    "LabResource",
    "OfficialChangeProposal",
    "StockMovement",
    "StockRequest",
    "TimetableSlot",
]
