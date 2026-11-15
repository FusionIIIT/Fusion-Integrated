"""Archival and retention policies for modules.system_admin.

Pure Python logic for assessing archival eligibility, reversible deadline
calculation, and purge retention eligibility.
Free of external dependencies (strictly NO Django, DRF, or Celery).
Traceability: BR-SA-004, BR-SA-005, BR-SA-021, ISS-SA-004.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from .dataclasses import ArchivalEligibilityVerdict


def assess_user_archival_eligibility(
    is_deactivated: bool,
    deactivated_at: Optional[datetime],
    has_pending_transactions: bool,
    min_deactivation_days: int,
    now: datetime,
) -> ArchivalEligibilityVerdict:
    """BR-SA-004: Only deactivated users with no pending transactions and
    elapsed deactivation interval are eligible."""
    if not is_deactivated or deactivated_at is None:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason="User must be in deactivated status.",
            has_pending_transactions=has_pending_transactions,
            deactivation_days_elapsed=0,
            required_deactivation_days=min_deactivation_days,
        )
    elapsed = (now - deactivated_at).days
    if has_pending_transactions:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason="User has pending workflow transactions or unreturned assets.",
            has_pending_transactions=True,
            deactivation_days_elapsed=elapsed,
            required_deactivation_days=min_deactivation_days,
        )
    if elapsed < min_deactivation_days:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason=f"Deactivation period of {elapsed} days is less than required {min_deactivation_days} days.",
            has_pending_transactions=False,
            deactivation_days_elapsed=elapsed,
            required_deactivation_days=min_deactivation_days,
        )
    return ArchivalEligibilityVerdict(
        is_eligible=True,
        reason="",
        has_pending_transactions=False,
        deactivation_days_elapsed=elapsed,
        required_deactivation_days=min_deactivation_days,
    )


def calculate_reversible_deadline(archived_at: datetime, reversible_window_days: int) -> datetime:
    """BR-SA-005 & ISS-SA-004: Calculates the exact timestamp when the account
    becomes permanently non-restorable."""
    return archived_at + timedelta(days=reversible_window_days)


def is_historical_data_purge_eligible(archived_at: date, retention_years: int, today: date) -> bool:
    """BR-SA-021: Purge eligible only after retention period has fully elapsed."""
    try:
        retention_cutoff = date(archived_at.year + retention_years, archived_at.month, archived_at.day)
    except ValueError:
        # Handles leap year edge cases (e.g., Feb 29 in non-leap year -> Feb 28)
        retention_cutoff = date(archived_at.year + retention_years, archived_at.month, archived_at.day - 1)
    return today >= retention_cutoff
