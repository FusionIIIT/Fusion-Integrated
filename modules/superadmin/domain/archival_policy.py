from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.utils import timezone as tz

from modules.superadmin.domain.exceptions import ArchivalIneligibleError


@dataclass(frozen=True)
class ArchivalEligibilityVerdict:
    is_eligible: bool
    reason: str = ""
    has_pending_transactions: bool = False
    deactivation_days_elapsed: int = 0
    required_deactivation_days: int = 30


def _ensure_aware(dt: datetime, reference: datetime) -> datetime:
    """Return *dt* as a timezone-aware datetime.

    If *dt* is already aware it is returned unchanged.  If it is naive it is
    made aware using the same tzinfo as *reference* (which is always the
    Django ``timezone.now()`` value and therefore always UTC-aware).
    """
    if dt.tzinfo is None:
        return tz.make_aware(dt, reference.tzinfo)
    return dt


def assess_user_archival_eligibility(
    *,
    is_deactivated: bool,
    deactivated_at: datetime | None,
    has_pending_transactions: bool,
    min_deactivation_days: int,
    now: datetime,
) -> ArchivalEligibilityVerdict:
    # BR-SA-004: Deactivated account and zero pending transactions check
    if not is_deactivated or deactivated_at is None:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason="User must be in deactivated status.",
            has_pending_transactions=has_pending_transactions,
            deactivation_days_elapsed=0,
            required_deactivation_days=min_deactivation_days,
        )
    # Guard: convert naive deactivated_at to aware before arithmetic (FR TC-057)
    deactivated_at = _ensure_aware(deactivated_at, now)
    if has_pending_transactions:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason="User has pending workflow transactions or unreturned assets.",
            has_pending_transactions=True,
            deactivation_days_elapsed=(now - deactivated_at).days,
            required_deactivation_days=min_deactivation_days,
        )
    elapsed = (now - deactivated_at).days
    if elapsed < min_deactivation_days:
        return ArchivalEligibilityVerdict(
            is_eligible=False,
            reason=(
                f"Deactivation period of {elapsed} days is less than "
                f"required {min_deactivation_days} days."
            ),
            has_pending_transactions=False,
            deactivation_days_elapsed=elapsed,
            required_deactivation_days=min_deactivation_days,
        )
    return ArchivalEligibilityVerdict(
        is_eligible=True,
        has_pending_transactions=False,
        deactivation_days_elapsed=elapsed,
        required_deactivation_days=min_deactivation_days,
    )


def calculate_reversible_deadline(archived_at: datetime, window_days: int) -> datetime:
    # BR-SA-005 & ISS-SA-004: Calculates restoration window expiry
    return archived_at + timedelta(days=window_days)


def is_historical_data_purge_eligible(retention_expires_at: date, today: date) -> bool:
    # BR-SA-021: Purge eligibility cutoff verification
    return today >= retention_expires_at


def assert_purge_eligible(retention_expires_at: date, today: date) -> None:
    # BR-SA-021: Raises exception when purge requested within retention window
    if not is_historical_data_purge_eligible(retention_expires_at, today):
        raise ArchivalIneligibleError(
            f"Dataset is within mandatory retention period until "
            f"{retention_expires_at.isoformat()}."
        )
