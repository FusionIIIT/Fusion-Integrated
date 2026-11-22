"""CMS policy helpers kept independent of Django and the HTTP layer."""

from dataclasses import dataclass

STATUSES = {"submitted", "in_progress", "resolved", "rejected", "closed"}
PRIORITIES = {"low", "medium", "high"}


@dataclass(frozen=True)
class Transition:
    source: str
    target: str


class InvalidTransition(ValueError):
    pass


def transition(source: str, target: str) -> Transition:
    """Only transitions defined by the synchronized STTs are accepted.

    In particular, no implicit entry to In Progress or non-verification
    closure is inferred from the open clarifications in the source documents.
    """
    if source == "submitted" and target in {"resolved", "rejected"}:
        return Transition(source, target)
    if source == "in_progress" and target in {"resolved", "rejected"}:
        return Transition(source, target)
    if source == "resolved" and target == "closed":
        return Transition(source, target)
    if source == "closed" and target in {"submitted", "in_progress"}:
        return Transition(source, target)
    raise InvalidTransition(f"Transition {source!r} to {target!r} is not supported.")


def is_unresolved(status: str) -> bool:
    return status in {"submitted", "in_progress"}
