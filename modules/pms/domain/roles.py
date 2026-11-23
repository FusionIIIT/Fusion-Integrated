"""Only the acting role counts: PMS permissions narrowed to the role a person is working as."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

OFFICES = frozenset({"pms_director", "pms_pcc_admin", "pms_attorney"})
PREFIX = "pms."


def acting_role(active_role: str | None, kind: str) -> str:
    """A PMS office when acting as one; otherwise the person's basic kind, an applicant."""
    return active_role if active_role in OFFICES else kind


def acting_permissions(permissions: Iterable[str], active_role: str | None, kind: str,
                       grants: Mapping[str, Iterable[str]]) -> frozenset[str]:
    """Keep other modules' codes; keep a PMS code only if the acting role itself is granted it."""
    held = frozenset(permissions)
    allowed = frozenset(grants.get(acting_role(active_role, kind), ()))
    return frozenset(p for p in held if not p.startswith(PREFIX) or p in allowed)
