"""Primitive domain vocabulary; none of these values map IAM designations."""

from enum import StrEnum


class DomainActor(StrEnum):
    """Business actors named by the specification, not IAM role names."""

    PROFESSOR = "Professor"
    STUDENT = "Student"
    SYSTEM = "System"


class QuizStatus(StrEnum):
    DRAFT = "Draft"
    SCHEDULED = "Scheduled"
    AVAILABLE = "Available"
    CLOSED = "Closed"
    ARCHIVED = "Archived"
    DELETED = "Deleted"  # Logical outcome; not a persisted Quiz status.


class AttemptStatus(StrEnum):
    IN_PROGRESS = "In Progress"
    SUBMITTED = "Submitted"


class ResultStatus(StrEnum):
    NOT_EVALUATED = "Not Evaluated"
    PARTIALLY_EVALUATED = "Partially Evaluated"
    EVALUATED = "Evaluated"
    RELEASED = "Released"
