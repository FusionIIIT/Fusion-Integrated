"""Automatic engineer assignment pure-python logic based on workload (BR-IWD-002)."""

from collections.abc import Mapping, Sequence


def select_best_engineer(
    eligible_engineer_ids: Sequence[int], workload_map: Mapping[int, int]
) -> int | None:
    """Select the engineer with the lowest active workload deterministically."""
    if not eligible_engineer_ids:
        return None

    return sorted(
        eligible_engineer_ids,
        key=lambda eid: (workload_map.get(eid, 0), eid),
    )[0]
