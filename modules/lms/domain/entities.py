"""Domain entities and value enums for LMS (Course Management).

Pure Python — no Django imports.
"""
from enum import Enum


class CourseRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    TA = "ta"
    OBSERVER = "observer"


class MaterialType(str, Enum):
    FILE = "file"
    LINK = "link"
    NOTE = "note"


class MaterialStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class SubmissionType(str, Enum):
    FILE = "file"
    TEXT = "text"
    LINK = "link"


class AssignmentStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    AVAILABLE = "available"


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"


class GradeStatus(str, Enum):
    DRAFT = "draft"
    RELEASED = "released"
