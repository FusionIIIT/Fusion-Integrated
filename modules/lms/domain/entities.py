"""Domain entities and value enums for LMS (Course Management).

Pure Python — no Django imports.
"""

from enum import StrEnum


class CourseRole(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    TA = "ta"
    OBSERVER = "observer"


class MaterialType(StrEnum):
    FILE = "file"
    LINK = "link"
    NOTE = "note"


class MaterialStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class SubmissionType(StrEnum):
    FILE = "file"
    TEXT = "text"
    LINK = "link"


class AssignmentStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    AVAILABLE = "available"


class SubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"


class GradeStatus(StrEnum):
    DRAFT = "draft"
    RELEASED = "released"
