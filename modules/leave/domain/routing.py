"""Resolving WHO acts: the Unit Head, and the configured higher-sanction path.

The specification is deliberately configuration-driven (BR-EL-019, BR-EL-030):
the path is resolved from the applicant, the organizational unit, the
designation/role, the leave category and the current hierarchy configuration.
Named roles — Deputy Registrar (Estt.), Dean, Registrar, Director — appear only
where configured, and the Establishment step is optional.

Nothing here imports Django: the configuration is handed in as plain values.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain import categories as cat
from modules.leave.domain.state_machine import ESTABLISHMENT, UNIT_HEAD

#: The designation that triggers the Director-specific self-sanction rule.
DIRECTOR_ROLE = "Director"


@dataclass(frozen=True)
class Hierarchy:
    """The current configuration, with no version lifecycle (BR-EL-030).

    `authority_path` is the ordered list of designations a higher-sanction
    request travels through after the Unit Head's recommendation. The
    Establishment step is a real step only when it is configured AND its
    designation appears in the path.
    """

    authority_path: tuple[str, ...] = ("Deputy Registrar", "Registrar")
    establishment_designation: str = "Deputy Registrar"
    establishment_step_enabled: bool = True


@dataclass(frozen=True)
class Path:
    """Where a request goes."""

    unit_head_user_id: int | None
    final_authority: str
    establishment_first: bool
    self_sanction: bool

    @property
    def steps(self) -> tuple[str, ...]:
        """The ordered actor lanes a request passes through."""
        out: list[str] = []
        if self.unit_head_user_id is not None:
            out.append(UNIT_HEAD)
        if self.establishment_first:
            out.append(ESTABLISHMENT)
        out.append("authority")
        return tuple(out)


def is_director(roles: tuple[str, ...]) -> bool:
    return DIRECTOR_ROLE in tuple(roles)


def resolve_path(*, category_code: str, roles: tuple[str, ...],
                 unit_head_user_id: int | None,
                 hierarchy: Hierarchy | None = None) -> Path:
    """The sanctioning path for a request (BR-EL-016..020).

    CL and RH, including their Station Leave, finish at the Unit Head. SCL, EL,
    COL and VL get a recommendation there and continue through the configured
    hierarchy. A Director applicant never travels the normal path at all.
    """
    h = hierarchy or Hierarchy()
    if is_director(roles):
        return Path(unit_head_user_id=None, final_authority=DIRECTOR_ROLE,
                    establishment_first=False, self_sanction=True)

    if cat.category(category_code).unit_head_final:
        return Path(unit_head_user_id=unit_head_user_id,
                    final_authority="Unit Head", establishment_first=False,
                    self_sanction=False)

    establishment_first = bool(h.establishment_step_enabled
                               and h.establishment_designation
                               and h.establishment_designation in h.authority_path)
    final = h.authority_path[-1] if h.authority_path else DIRECTOR_ROLE
    return Path(unit_head_user_id=unit_head_user_id, final_authority=final,
                establishment_first=establishment_first, self_sanction=False)
