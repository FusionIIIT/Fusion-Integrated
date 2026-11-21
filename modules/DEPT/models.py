"""Module-owned Department data shape.

Persistence is deliberately not coupled to Django yet: the host settings and
database schema cannot be changed as part of this isolated module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Department:
    """A named organizational unit with an optional parent department."""

    id: int
    code: str
    name: str
    description: str = ""
    parent_id: int | None = None
    is_active: bool = True
