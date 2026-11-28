"""Display names for the people a page shows, from the directory in one batched call."""
from __future__ import annotations

from collections.abc import Iterable

from modules.directory import contracts as directory


def names_for(user_ids: Iterable[int | None]) -> dict[int, str]:
    """{user_id: "Name (username)"}; an id the directory does not know is simply absent."""
    ids = sorted({int(i) for i in user_ids if i is not None})
    return {uid: f"{p.display_name} ({p.username})"
            for uid, p in directory.get_users(ids).items()}
