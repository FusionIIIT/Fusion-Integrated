"""Valid ELM request transitions without framework dependencies."""

from collections import defaultdict

PENDING = {
    "awaiting_substitute",
    "applicant_action_required",
    "awaiting_unit_head",
    "awaiting_establishment",
    "awaiting_final_sanction",
    "awaiting_director_self",
}

TRANSITIONS: dict[str, set[str]] = defaultdict(set)
for _state in PENDING:
    TRANSITIONS[_state].add("withdrawn")
TRANSITIONS["awaiting_substitute"].update(
    {"applicant_action_required", "awaiting_unit_head", "awaiting_director_self"}
)
TRANSITIONS["awaiting_unit_head"].add("awaiting_substitute")
TRANSITIONS["applicant_action_required"].add("awaiting_substitute")
TRANSITIONS["awaiting_unit_head"].update(
    {
        "awaiting_establishment",
        "awaiting_final_sanction",
        "awaiting_director_self",
        "approved",
        "rejected",
    }
)
TRANSITIONS["awaiting_establishment"].add("awaiting_final_sanction")
TRANSITIONS["awaiting_final_sanction"].update({"approved", "rejected"})
TRANSITIONS["awaiting_director_self"].update({"approved", "rejected"})
TRANSITIONS["approved"].add("cancelled")


def validate_status_change(current: str, target: str) -> None:
    if current == target:
        return
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid ELM request transition: {current} -> {target}.")
