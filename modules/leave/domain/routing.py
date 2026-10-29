"""Authority resolution and routing (BR-EL-016..020).

The specification never names a production hierarchy, so routing is resolved
from configuration: an ordered chain of steps per leave category and
organisational unit. Which designation fills each step is a configured string,
so no institute-specific name is baked into the module.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm

UNIT_HEAD_STEP = "unit_head"
ESTABLISHMENT_STEP = "establishment"
FINAL_SANCTION_STEP = "final_sanction"
DIRECTOR_SELF_SANCTION_STEP = "director_self_sanction"

STEP_KINDS: tuple[str, ...] = (UNIT_HEAD_STEP, ESTABLISHMENT_STEP,
                               FINAL_SANCTION_STEP, DIRECTOR_SELF_SANCTION_STEP)

#: CL and RH stop at the Unit Head; everything else continues (BR-EL-016/017).
UNIT_HEAD_FINAL: frozenset[str] = frozenset({cat.CASUAL, cat.RESTRICTED_HOLIDAY})

#: Resumption and extension apply to these only (BR-EL-025, BR-EL-027).
ONGOING_CATEGORIES: frozenset[str] = frozenset({cat.EARNED, cat.COMMUTED,
                                                cat.VACATION})

#: Step labels are configurable designations; these are the spec's own names.
DEFAULT_DESIGNATIONS: dict[str, str] = {
    UNIT_HEAD_STEP: "Unit Head",
    ESTABLISHMENT_STEP: "Deputy Registrar (Estt.)",
    FINAL_SANCTION_STEP: "Sanctioning Authority",
    DIRECTOR_SELF_SANCTION_STEP: "Director",
}


class RoutingError(Exception):
    """No configured route can carry this request."""


@dataclass(frozen=True)
class RouteStep:
    kind: str
    order: int
    #: A configured designation string, resolved to a person at configuration time.
    designation: str = ""
    #: A pinned person; when null the step is unassigned and blocks the request.
    user_id: int | None = None

    @property
    def assigned(self) -> bool:
        return self.user_id is not None


@dataclass(frozen=True)
class Route:
    steps: tuple[RouteStep, ...] = ()

    def step(self, kind: str) -> RouteStep | None:
        for candidate in self.steps:
            if candidate.kind == kind:
                return candidate
        return None

    @property
    def unassigned(self) -> list[RouteStep]:
        return [s for s in self.steps if not s.assigned]


def is_unit_head_final(category: str) -> bool:
    return category in UNIT_HEAD_FINAL


def requires_establishment(policy_establishment_enabled: bool) -> bool:
    """BR-EL-019: the Establishment step runs only where configured."""
    return policy_establishment_enabled


def submission_target(*, category: str, applicant_is_director: bool,
                      has_unit_head: bool,
                      substitute_required: bool) -> str:
    """Where a valid new request first lands (CW-EL-01 STT rows 1-3)."""
    if substitute_required:
        return sm.AWAITING_SUBSTITUTE
    if applicant_is_director:
        return sm.AWAITING_DIRECTOR
    if has_unit_head:
        return sm.AWAITING_UNIT_HEAD
    raise RoutingError(
        "No Unit Head is configured for this employee's organisational unit, so "
        "the request has nobody who can review it. Ask the Leave Administrator "
        "to configure the unit.")


def after_unit_head(*, category: str, establishment_configured: bool) -> str:
    """A Unit Head on higher-sanction leave records a recommendation either way
    (BR-EL-017), so both branches continue rather than terminating."""
    if is_unit_head_final(category):
        raise RoutingError(
            "CL and RH are decided by the Unit Head; there is no higher step.")
    return (sm.AWAITING_ESTABLISHMENT if establishment_configured
            else sm.AWAITING_FINAL_DECISION)


def after_unit_head_cancellation(*, category: str,
                                 establishment_configured: bool) -> str:
    """Cancellation follows the same hierarchy (BR-EL-023)."""
    if is_unit_head_final(category):
        raise RoutingError(
            "CL and RH cancellation is decided by the Unit Head; there is no "
            "higher step.")
    return (sm.CANCEL_PENDING_ESTABLISHMENT if establishment_configured
            else sm.CANCEL_PENDING_FINAL)


def actor_role_for(step_kind: str) -> str:
    return {
        UNIT_HEAD_STEP: sm.UNIT_HEAD,
        ESTABLISHMENT_STEP: sm.ESTABLISHMENT,
        FINAL_SANCTION_STEP: sm.SANCTIONING_AUTHORITY,
        DIRECTOR_SELF_SANCTION_STEP: sm.DIRECTOR,
    }[step_kind]