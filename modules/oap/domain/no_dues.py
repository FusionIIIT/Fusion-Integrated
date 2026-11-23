"""Derived no-dues case state from the seven domain results (OA-BR-33)."""

from __future__ import annotations

from collections.abc import Mapping

DOMAINS = (
    "library",
    "hostel",
    "mess",
    "department",
    "lab",
    "academic_section",
    "student_section",
)

PENDING = "pending"
CLEAR = "clear"
OUTSTANDING = "outstanding"

IN_PROGRESS = "in_progress"
DUES_OUTSTANDING = "dues_outstanding"
ALL_CLEAR = "all_clear"
FINALIZED = "finalized"


def derive_status(results: Mapping[str, str], *, finalized: bool) -> str:
    if finalized:
        return FINALIZED
    values = [results.get(d, PENDING) for d in DOMAINS]
    if any(v == PENDING for v in values):
        return IN_PROGRESS
    if all(v == CLEAR for v in values):
        return ALL_CLEAR
    return DUES_OUTSTANDING


def may_finalize(results: Mapping[str, str], *, finalized: bool) -> bool:
    return derive_status(results, finalized=finalized) == ALL_CLEAR
