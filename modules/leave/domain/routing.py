"""Authority resolution along the configured hierarchy (BR-EL-016..020).

The path is a function of the applicant, the leave category and the current
hierarchy configuration (BR-EL-030), never of a hard-coded office name: a
hierarchy step the institute has not configured does not exist.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain import categories as cat
from modules.leave.domain.errors import RuleViolation

UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
FINAL_AUTHORITY = "final_authority"

KINDS: tuple[str, ...] = (UNIT_HEAD, ESTABLISHMENT, FINAL_AUTHORITY)

#: The self-sanction route is keyed by designation, and configuration owns it.
DEFAULT_SELF_SANCTION_DESIGNATION = "Director"


@dataclass(frozen=True)
class ConfiguredStep:
    """One row of the current hierarchy configuration, as stored."""

    sequence: int
    kind: str
    designation: str
    #: Empty means the step applies to every leave category.
    categories: tuple[str, ...] = ()

    def applies_to(self, category: str) -> bool:
        return not self.categories or category in self.categories


@dataclass(frozen=True)
class Path:
    """Where a request goes, and who is expected to act at each hop."""

    unit_head: ConfiguredStep | None = None
    establishment: ConfiguredStep | None = None
    final: ConfiguredStep | None = None
    unit_head_final: bool = False
    self_sanction: bool = False

    @property
    def steps(self) -> tuple[ConfiguredStep, ...]:
        return tuple(s for s in (self.unit_head, self.establishment, self.final)
                     if s is not None)

    @property
    def first_designation(self) -> str:
        return self.unit_head.designation if self.unit_head else ""

    @property
    def establishment_designation(self) -> str:
        return self.establishment.designation if self.establishment else ""

    @property
    def final_designation(self) -> str:
        return self.final.designation if self.final else ""


def ordered(steps: tuple[ConfiguredStep, ...]) -> tuple[ConfiguredStep, ...]:
    return tuple(sorted(steps, key=lambda s: (s.sequence, s.designation)))


def resolve(*, category: str, steps: tuple[ConfiguredStep, ...],
            self_sanction_designation: str = DEFAULT_SELF_SANCTION_DESIGNATION,
            applicant_role: str = "") -> Path:
    """The path this request takes from submission to a final decision."""
    if applicant_role and applicant_role == self_sanction_designation:
        return Path(self_sanction=True)

    applicable = ordered(tuple(s for s in steps if s.applies_to(category)))
    unit_head = next((s for s in applicable if s.kind == UNIT_HEAD), None)
    if unit_head is None:
        raise RuleViolation(
            f"No Unit Head is configured for {category} leave. An administrator "
            "has to configure the hierarchy first.",
            code="routing_not_configured")

    if cat.unit_head_is_final(category):
        # BR-EL-016: the Unit Head IS the final authority for CL and RH.
        return Path(unit_head=unit_head, unit_head_final=True)

    final = next((s for s in applicable if s.kind == FINAL_AUTHORITY), None)
    if final is None:
        raise RuleViolation(
            f"No final sanctioning authority is configured for {category} leave. "
            "An administrator has to configure the hierarchy first.",
            code="routing_not_configured")

    establishment = next((s for s in applicable if s.kind == ESTABLISHMENT), None)
    return Path(unit_head=unit_head, establishment=establishment, final=final)


def request_validator(path: Path) -> str:
    """Which permission the next hop's actor needs, for the audit line."""
    return "leave.request.approve" if path.self_sanction else "leave.request.review"
