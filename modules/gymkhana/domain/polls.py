"""Poll domain logic (BR-GYM-012, BR-GYM-013, BR-GYM-014).

Pure Python: no Django/database dependencies.
"""
from __future__ import annotations

from collections.abc import Sequence

from modules.gymkhana.domain.exceptions import (
    InvalidPollChoicesError,
    InvalidVoteChoiceError,
)


def validate_poll_choices(choices: Sequence[str]) -> list[str]:
    """Validate that a poll has at least two non-empty, distinct choices (BR-GYM-012)."""
    if not choices or len(choices) < 2:
        raise InvalidPollChoicesError("A voting poll must have at least two choices.")

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in choices:
        text = (raw or "").strip()
        if not text:
            raise InvalidPollChoicesError("Poll choices cannot be blank.")
        if text.lower() in seen:
            raise InvalidPollChoicesError(f"Duplicate poll choice: {text!r}.")
        seen.add(text.lower())
        cleaned.append(text)

    if len(cleaned) < 2:
        raise InvalidPollChoicesError("A voting poll must have at least two distinct choices.")
    return cleaned


def is_student_targeted(
    batch_year: int | None,
    discipline: str,
    targets: Sequence[dict],
) -> bool:
    """Evaluate whether a student matches any of the poll target criteria (BR-GYM-013, BR-GYM-014).

    Each target entry has:
      - batch_year: int
      - discipline: str ('all' or specific branch like 'CSE')
    """
    if batch_year is None:
        return False

    student_disc = (discipline or "").strip().upper()

    for target in targets:
        target_batch = target.get("batch_year")
        if target_batch != batch_year:
            continue

        target_disc = (target.get("discipline") or "all").strip().upper()
        if target_disc in ("ALL", ""):
            return True
        if target_disc == student_disc:
            return True

    return False


def validate_poll_vote_choice(poll_id: int, choice_poll_id: int) -> None:
    """Service invariant: verify that the selected choice belongs to the target poll."""
    if choice_poll_id != poll_id:
        raise InvalidVoteChoiceError(
            f"Choice belongs to poll {choice_poll_id}, but vote was cast in poll {poll_id}."
        )
