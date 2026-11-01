"""Announcement targeting (BR-DEPT-002, BR-DEPT-003).

An empty target list means "everyone" on that axis. The specification leaves
wildcard behaviour open (BR-DEPT-002 exceptions), so that is the documented
assumption: a narrower announcement lists values, a broad one lists none.
"""
from __future__ import annotations

from dataclasses import dataclass

ROLES = ("student", "faculty")


@dataclass(frozen=True)
class Viewer:
    role: str                    # "student" | "faculty" | anything else
    programme: str = ""
    batch_year: int | None = None


class IncompleteAnnouncement(ValueError):
    pass


def validate_publication(title: str, body: str, roles: list[str],
                         programmes: list[str], years: list[int]) -> None:
    """BR-DEPT-003: content, and targeting that can actually be filtered on."""
    if not (title or "").strip() or not (body or "").strip():
        raise IncompleteAnnouncement("An announcement needs a title and a body.")
    bad = [r for r in roles if r not in ROLES]
    if bad:
        raise IncompleteAnnouncement(f"Unknown target role(s): {bad}. "
                                     f"Use {list(ROLES)}.")
    if any(not str(p).strip() for p in programmes):
        raise IncompleteAnnouncement("A target programme cannot be blank.")
    if any(not isinstance(y, int) or y < 1990 or y > 2100 for y in years):
        raise IncompleteAnnouncement("Target years must be four-digit years.")


def is_visible(*, roles: list[str], programmes: list[str], years: list[int],
               viewer: Viewer) -> bool:
    """All three axes must match; an empty axis matches everyone."""
    if roles and viewer.role not in roles:
        return False
    if programmes and viewer.programme not in programmes:
        return False
    # a year-targeted notice has no meaning for someone without a batch
    return not years or viewer.batch_year in years
