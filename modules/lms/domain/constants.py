"""LMS domain constants and enumerations. Pure Python."""

from __future__ import annotations


class CourseRole:
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    TA = "TA"
    OBSERVER = "OBSERVER"

    ALL = (STUDENT, INSTRUCTOR, TA, OBSERVER)


class MembershipStatus:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    ALL = (ACTIVE, INACTIVE)


class MaterialType:
    FILE = "FILE"
    LINK = "LINK"
    NOTE = "NOTE"

    ALL = (FILE, LINK, NOTE)


class MaterialStatus:
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

    ALL = (DRAFT, SCHEDULED, PUBLISHED, ARCHIVED)


class SubmissionType:
    FILE = "FILE"
    TEXT = "TEXT"
    LINK = "LINK"

    ALL = (FILE, TEXT, LINK)


class AssignmentStatus:
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"

    ALL = (DRAFT, SCHEDULED, PUBLISHED, CLOSED, ARCHIVED)


class SubmissionStatus:
    SUBMITTED = "SUBMITTED"

    ALL = (SUBMITTED,)


class GradeStatus:
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"

    ALL = (DRAFT, PUBLISHED)
