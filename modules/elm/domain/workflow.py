"""ELM request-state vocabulary shared by services and focused domain checks."""

from __future__ import annotations

AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL = "awaiting_final"
AWAITING_DIRECTOR = "awaiting_director"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"

PENDING_STATES = frozenset(
    {
        AWAITING_SUBSTITUTE,
        APPLICANT_ACTION_REQUIRED,
        AWAITING_UNIT_HEAD,
        AWAITING_ESTABLISHMENT,
        AWAITING_FINAL,
        AWAITING_DIRECTOR,
    }
)
TERMINAL_STATES = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED})


def is_pending(status: str) -> bool:
    return status in PENDING_STATES


def next_after_unit_head(
    *, category: str, establishment_required: bool, director_applicant: bool = False
) -> str:
    if director_applicant:
        return AWAITING_DIRECTOR
    if category in {"CL", "RH"}:
        return "unit_head_final"
    return AWAITING_ESTABLISHMENT if establishment_required else AWAITING_FINAL
