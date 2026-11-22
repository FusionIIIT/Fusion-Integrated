"""Pure Python status and grading calculations."""

from __future__ import annotations

from datetime import datetime


def compute_submission_status(has_submitted: bool, due_date: datetime, now: datetime) -> str:
    """Computes a human-readable summary of student submission standing."""
    if has_submitted:
        return "SUBMITTED"
    if now > due_date:
        return "MISSING"
    return "PENDING"
