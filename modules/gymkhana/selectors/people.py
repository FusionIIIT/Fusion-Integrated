"""Directory lookups Gymkhana needs, always batched."""

from __future__ import annotations

from collections.abc import Iterable

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import ALL_GROUPS
from modules.gymkhana.selectors.errors import DirectoryUnavailableError

AUDIENCE_PAGE = 200
MAX_PEOPLE = 10


def student_group(user_id: int) -> tuple[str | None, str | None]:
    """A student's batch and branch, or None for whichever the directory does not hold."""
    user = get_users([user_id]).get(user_id)
    if user is None:
        return None, None
    return (str(user.batch_year) if user.batch_year else None, user.discipline or None)


def display_names(user_ids: Iterable[int | None]) -> dict[int, str]:
    ids = {i for i in user_ids if i is not None}
    return {uid: u.display_name for uid, u in get_users(sorted(ids)).items()}


def search_people(q: str, kind: str) -> list[dict]:
    """Type-ahead by username, returning nothing beyond what a picker needs."""
    try:
        rows = get_client().search_users(q=q, kind=kind, limit=MAX_PEOPLE)
    except IamUnavailable as exc:
        raise DirectoryUnavailableError from exc
    return [
        {"user_id": r.user_id, "username": r.username, "display_name": r.display_name}
        for r in rows
        if r.kind == kind and r.is_active
    ]


def poll_group_options() -> dict:
    """The batches and branches that actually exist."""
    try:
        found = get_client().academic_filters()
    except IamUnavailable as exc:
        raise DirectoryUnavailableError from exc
    return {
        "batches": [str(b) for b in found.get("batch_years", [])],
        "branches": [str(d) for d in found.get("disciplines", [])],
    }


def students_in_groups(groups: Iterable[tuple[str, str]]) -> list[int]:
    """Every student in the given batch and branch groups; only ids are kept."""
    ids: set[int] = set()
    for batch, branch in groups:
        filters = {}
        if batch != ALL_GROUPS:
            filters["batch_year"] = batch
        if branch != ALL_GROUPS:
            filters["discipline"] = branch
        offset = 0
        while True:
            page = get_client().academic_directory(limit=AUDIENCE_PAGE, offset=offset, **filters)
            rows = page.get("results", [])
            ids.update(int(row["user_id"]) for row in rows)
            offset += len(rows)
            if not rows or offset >= int(page.get("count", 0)):
                break
    return sorted(ids)
