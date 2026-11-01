"""Pure domain errors for LMS Course Management."""
from __future__ import annotations


class LMSRuleError(ValueError):
    """Base exception for all LMS domain rule violations."""


class CourseAccessDeniedError(LMSRuleError):
    """Raised when an unlinked or unauthorized user attempts course workspace access."""


class CourseEditingDeniedError(LMSRuleError):
    """Raised when a non-faculty or unassigned user attempts course workspace edits."""
