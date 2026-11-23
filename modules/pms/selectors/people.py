"""Finding a person by name for a picker: the IAM's own search, names and kinds only."""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client

MIN_QUERY = 2


@dataclass(frozen=True)
class Person:
    user_id: int
    display_name: str
    kind: str


def search(q: str, *, kind: str | None = None, limit: int = 20) -> list[Person] | None:
    """None when the IAM cannot be asked, which the caller reports instead of an empty list."""
    text = (q or "").strip()
    if len(text) < MIN_QUERY:
        return []
    try:
        refs = get_client().search_users(q=text[:100], kind=kind, limit=limit)
    except IamUnavailable:
        return None
    return [Person(r.user_id, r.display_name, r.kind) for r in refs]
