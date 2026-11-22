"""Pure Python business rules for LMS."""

from __future__ import annotations

from datetime import datetime


def is_submission_ontime(submitted_at: datetime, due_date: datetime) -> bool:
    """BR-LMS-013: Baseline on-time submission check."""
    return submitted_at <= due_date


def is_content_released(release_date: datetime | None, current_time: datetime) -> bool:
    """BR-LMS-005 & BR-LMS-011: Visibility trigger check."""
    if release_date is None:
        return True
    return release_date <= current_time
