"""Who may be assigned a review or a case, and in what order to offer them."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from modules.pms.domain.errors import RuleViolation


@dataclass(frozen=True)
class Candidate:
    user_id: int
    domain_codes: frozenset[str]
    workload: int


def conflicts(user_id: int, applicant_user_id: int, inventor_user_ids: Iterable[int]) -> bool:
    """BR-PMS-025 / 026 / 044: the applicant and every inventor are conflicted."""
    return user_id == applicant_user_id or user_id in set(inventor_user_ids)


def eligible_directors(candidates: Iterable[Candidate], domain_code: str,
                       applicant_user_id: int,
                       inventor_user_ids: Iterable[int]) -> list[Candidate]:
    """BR-PMS-023..026: unconflicted, area matches (blueprint Q-8), least loaded first."""
    inventors = set(inventor_user_ids)
    eligible = [c for c in candidates
                if domain_code in c.domain_codes
                and not conflicts(c.user_id, applicant_user_id, inventors)]
    return sorted(eligible, key=lambda c: (c.workload, c.user_id))


def check_director(director_user_id: int, candidates: Iterable[Candidate], domain_code: str,
                   applicant_user_id: int, inventor_user_ids: Iterable[int]) -> None:
    """The chosen Director must be one `eligible_directors` would offer."""
    inventors = set(inventor_user_ids)
    if conflicts(director_user_id, applicant_user_id, inventors):
        raise RuleViolation("That Director is the applicant or an inventor on this "
                            "application, so they cannot review it. Choose another.",
                            code="director_conflicted")
    pool = {c.user_id: c for c in candidates}
    chosen = pool.get(director_user_id)
    if chosen is None:
        raise RuleViolation("That person is not an active Director on the PMS roster.",
                            code="director_not_on_roster")
    if domain_code not in chosen.domain_codes:
        raise RuleViolation("That Director's areas do not include this application's area. "
                            "Choose a Director listed for it.", code="director_area_mismatch")


def rank_attorneys(panel: Iterable[Candidate], domain_code: str, applicant_user_id: int,
                   inventor_user_ids: Iterable[int],
                   preferred_user_id: int | None) -> list[Candidate]:
    """BR-PMS-042..045: matching, unconflicted panel attorneys; a panel preference first."""
    inventors = set(inventor_user_ids)
    eligible = [c for c in panel
                if domain_code in c.domain_codes
                and not conflicts(c.user_id, applicant_user_id, inventors)]
    return sorted(eligible, key=lambda c: (c.user_id != preferred_user_id, c.workload,
                                           c.user_id))


def check_attorney(attorney_user_id: int, panel: Iterable[Candidate], domain_code: str,
                   applicant_user_id: int, inventor_user_ids: Iterable[int],
                   exception_reason: str) -> bool:
    """BR-PMS-041 / 042 / 044; returns True when the assignment rests on an exception."""
    if conflicts(attorney_user_id, applicant_user_id, set(inventor_user_ids)):
        raise RuleViolation("That attorney is the applicant or an inventor on this "
                            "application. Choose another.", code="attorney_conflicted")
    pool = {c.user_id: c for c in panel}
    chosen = pool.get(attorney_user_id)
    eligible = chosen is not None and domain_code in chosen.domain_codes
    if eligible:
        return False
    if not exception_reason.strip():
        why = ("is not on the approved panel" if chosen is None
               else "is not listed for this application's area")
        raise RuleViolation(f"That attorney {why}. Record the institutional exception that "
                            f"permits the assignment, or choose a panel attorney.",
                            code="attorney_not_eligible")
    return True
