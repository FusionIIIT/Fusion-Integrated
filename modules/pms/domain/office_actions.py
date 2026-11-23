"""Office-action response deadlines, tracked only where the deadline is known."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from modules.pms.domain.errors import InvalidInput, RuleViolation


def current_deadline(original: date | None, extensions: Iterable[date]) -> date | None:
    """The latest granted extension replaces the original deadline."""
    later = sorted(extensions)
    return later[-1] if later else original


def tracked(deadline: date | None) -> bool:
    """BR-PMS-066 / BR-PMS-099: no deadline data, no tracking and no invented date."""
    return deadline is not None


def check_submission(submitted_on: date, deadline: date | None, today: date) -> None:
    """BR-PMS-065: recorded within the deadline unless an extension moved it."""
    if submitted_on > today:
        raise InvalidInput("The submission date cannot be in the future.",
                           code="date_in_future")
    if deadline is not None and submitted_on > deadline:
        raise RuleViolation(
            f"The response deadline was {deadline.isoformat()}. Record the extension the "
            f"office granted first, or report the missed deadline to PCC_ADMIN.",
            code="response_deadline_missed")


def check_extension(new_deadline: date, current: date | None, reason: str) -> str:
    if current is not None and new_deadline <= current:
        raise InvalidInput("An extension must move the deadline later than "
                           f"{current.isoformat()}.", code="extension_not_later")
    cleaned = (reason or "").strip()
    if not cleaned:
        raise InvalidInput("Record why the extension was requested.", code="reason_required")
    return cleaned[:2000]
