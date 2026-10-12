"""Category properties and route resolution (BR-EL-016..BR-EL-020).

Which authority finally decides, and whether a substitute/establishment step is
on the path, are asked here so the answer exists in exactly one place.
"""
from __future__ import annotations

from modules.elm.domain import enums as e


def is_continuous(category: str) -> bool:
    return category in e.CONTINUOUS


def allows_half_day(category: str) -> bool:
    return category in e.HALF_DAY


def is_unit_head_final(category: str) -> bool:
    return category in e.UNIT_HEAD_FINAL


def is_higher_sanction(category: str) -> bool:
    return category in e.HIGHER_SANCTION


def requires_resumption(category: str) -> bool:
    return category in e.RESUMPTION


def allows_extension(category: str) -> bool:
    return category in e.EXTENSION


def is_faculty_only(category: str) -> bool:
    return category in e.FACULTY_ONLY


def initial_status(*, substitute_required: bool, applicant_is_director: bool) -> str:
    """Where a freshly submitted request lands (CW-EL-01)."""
    if substitute_required:
        return e.AWAITING_SUBSTITUTE
    if applicant_is_director:
        return e.AWAITING_DIRECTOR_SANCTION
    return e.AWAITING_UNIT_HEAD


def status_after_substitute(*, applicant_is_director: bool) -> str:
    if applicant_is_director:
        return e.AWAITING_DIRECTOR_SANCTION
    return e.AWAITING_UNIT_HEAD


def status_after_unit_head(*, category: str, establishment_required: bool) -> str:
    """Where a recommendation from the Unit Head sends a higher-sanction case.

    For a Unit-Head-final category the caller chooses approve/reject instead, so
    this is only consulted on the higher-sanction path.
    """
    if establishment_required:
        return e.AWAITING_ESTABLISHMENT
    return e.AWAITING_FINAL_SANCTION


def task_type_for(status: str) -> str:
    return {
        e.AWAITING_SUBSTITUTE: e.T_SUBSTITUTE,
        e.AWAITING_UNIT_HEAD: e.T_UNIT_HEAD,
        e.AWAITING_ESTABLISHMENT: e.T_ESTABLISHMENT,
        e.AWAITING_FINAL_SANCTION: e.T_FINAL_SANCTION,
        e.AWAITING_DIRECTOR_SANCTION: e.T_DIRECTOR_SANCTION,
    }.get(status, e.T_UNIT_HEAD)
