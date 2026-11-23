"""Pure Python business rules for LMS."""

from __future__ import annotations

from datetime import datetime

from modules.lms.domain.constants import CourseRole


def is_submission_ontime(submitted_at: datetime, due_date: datetime) -> bool:
    """BR-LMS-013 & AFR-LMS-008.2: Baseline on-time submission check."""
    return submitted_at <= due_date


def is_content_released(release_date: datetime | None, current_time: datetime) -> bool:
    """BR-LMS-005 & BR-LMS-011: Visibility trigger check."""
    if release_date is None:
        return True
    return release_date <= current_time


def validate_release_date(release_date: datetime | None, current_time: datetime) -> bool:
    """AFR-LMS-003.3: Configure future release date/time validation."""
    if release_date is None:
        return True
    return release_date >= current_time


def can_update_course_details(role: str) -> bool:
    """AFR-LMS-002.1: Allow Faculty to configure course workspace settings."""
    return role == CourseRole.INSTRUCTOR


def can_post_announcement(role: str, can_post_flag: bool = False) -> bool:
    """AFR-LMS-005.2 & BR-LMS-007: Permitted TAs post announcements when authorized."""
    if role == CourseRole.INSTRUCTOR:
        return True
    if role == CourseRole.TA:
        return can_post_flag
    return False


def can_author_assignment(role: str) -> bool:
    """AFR-LMS-014.3 & BR-LMS-004: TA cannot create, edit, or publish assignments."""
    return role == CourseRole.INSTRUCTOR


def can_author_material(role: str) -> bool:
    """AFR-LMS-014.4 & BR-LMS-004: TA cannot create or edit course materials."""
    return role == CourseRole.INSTRUCTOR


def can_manage_workspace(role: str) -> bool:
    """AFR-LMS-014.5: TA cannot modify course structure or workspace settings."""
    return role == CourseRole.INSTRUCTOR


def can_grade_submission(role: str, can_grade_flag: bool = True) -> bool:
    """CFR-LMS-014 & AFR-LMS-010.2: TA grades student submissions for assigned course."""
    if role == CourseRole.INSTRUCTOR:
        return True
    if role == CourseRole.TA:
        return can_grade_flag
    return False


def can_release_grades(role: str) -> bool:
    """AFR-LMS-011.3 & BR-LMS-017: Allow Faculty to release grades and feedback."""
    return role == CourseRole.INSTRUCTOR
