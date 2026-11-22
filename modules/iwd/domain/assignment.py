from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineerCandidate:
    engineer_id: int
    discipline: str  # 'civil' or 'electrical'
    active_load: int


def select_best_engineer(
    category: str,
    candidates: Sequence[EngineerCandidate],
) -> int:
    """Selects an engineer by matching discipline and minimizing active workload (BR-IWD-002)."""
    matching = [c for c in candidates if c.discipline.lower() == category.lower()]
    pool = matching if matching else list(candidates)
    if not pool:
        raise ValueError("No eligible engineers available for assignment.")
    # Sort primarily by active load, secondarily by engineer_id for deterministic assignment
    sorted_pool = sorted(pool, key=lambda x: (x.active_load, x.engineer_id))
    return sorted_pool[0].engineer_id
