"""ELM sanctioning-path resolution (PS §7, BR-EL-016…020).

Pure logic over the applicant's context and the configured
hierarchy. The resulting :class:`Route` is a snapshot: it is stored
on the request so later reviews replay exactly the path that was
valid when the application was submitted, even if the configuration
changes mid-flight.

The three canonical paths:

* **CL / RH** — the Unit Head is the final authority.
* **SCL / EL / COL / VL** — the Unit Head records a
  Recommendation, the request optionally passes through
  Establishment processing, and the configured Sanctioning
  Authority (Deputy Registrar (Estt.), Dean, Registrar, Director …)
  makes the final decision.
* **Director as applicant** — the Director self-sanctions; the
  request never passes through lower authorities (BR-EL-019).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.elm.domain.leave_types import (
    ACTOR_EMPLOYEE,
    ACTOR_ESTABLISHMENT,
    ACTOR_SANCTIONING,
    ACTOR_UNIT_HEAD,
    HIGHER_SANCTION_CATEGORIES,
    UNIT_HEAD_FINAL_CATEGORIES,
)

#: Roles a route step can assign work to.
ROLE_UNIT_HEAD = "unit_head"
ROLE_ESTABLISHMENT = "establishment"
ROLE_SANCTIONING_AUTHORITY = "sanctioning_authority"
ROLE_DIRECTOR_SELF = "director_self_sanction"
ROLE_SUBSTITUTE = "substitute"

#: Decision weight of a step.
DECISION_FINAL = "final"
DECISION_RECOMMENDATION = "recommendation"
DECISION_ROUTING = "routing"


@dataclass(frozen=True)
class ApplicantContext:
    """Who is applying — everything routing needs about a person."""

    user_id: int
    employee_kind: str            # faculty | staff
    designation_name: str
    unit_code: str

    @property
    def is_director(self) -> bool:
        return self.designation_name == DIRECTOR_DESIGNATION


#: The designation that self-sanctions (BR-EL-019). PolicyConfig
#: holds the configured list; this is the canonical default.
DIRECTOR_DESIGNATION = "Director"


@dataclass(frozen=True)
class HierarchyProfile:
    """The routing configuration that applies to one request."""

    establishment_required: bool
    establishment_designations: tuple[str, ...]
    sanctioning_authority: str
    director_designations: tuple[str, ...] = (DIRECTOR_DESIGNATION,)

    def is_director(self, designation: str) -> bool:
        return designation in self.director_designations

    def is_establishment(self, designation: str) -> bool:
        return designation in self.establishment_designations


@dataclass(frozen=True)
class RouteStep:
    role: str
    decision: str
    authority: str | None = None


@dataclass(frozen=True)
class Route:
    """Ordered processing steps for one application."""

    steps: tuple[RouteStep, ...] = field(default_factory=tuple)
    director_path: bool = False

    def __iter__(self):
        return iter(self.steps)

    @property
    def final_step(self) -> RouteStep:
        return self.steps[-1]


def resolve_route(applicant: ApplicantContext, category: str,
                  hierarchy: HierarchyProfile) -> Route:
    """Resolve the sanctioning path for ``applicant`` and ``category``.

    Raises nothing: an unknown category simply takes the
    higher-sanction path, which is the safe default (the category
    itself is validated earlier, at submission).
    """
    if hierarchy.is_director(applicant.designation_name):
        # BR-EL-019: a Director's own application is self-sanctioned.
        return Route(steps=(RouteStep(ROLE_DIRECTOR_SELF, DECISION_FINAL),),
                     director_path=True)

    if category in UNIT_HEAD_FINAL_CATEGORIES:
        return Route(steps=(RouteStep(ROLE_UNIT_HEAD, DECISION_FINAL),))

    if category in HIGHER_SANCTION_CATEGORIES:
        steps = [RouteStep(ROLE_UNIT_HEAD, DECISION_RECOMMENDATION)]
        if hierarchy.establishment_required:
            steps.append(RouteStep(ROLE_ESTABLISHMENT, DECISION_ROUTING))
        steps.append(RouteStep(
            ROLE_SANCTIONING_AUTHORITY, DECISION_FINAL,
            hierarchy.sanctioning_authority,
        ))
        return Route(steps=tuple(steps))

    # Unknown category: route like a higher-sanction request.
    return resolve_route(applicant, "SCL", hierarchy)


def route_task_classes(route: Route) -> tuple[str, ...]:
    """Workflow task classes for a route, in processing order."""
    mapping = {
        ROLE_SUBSTITUTE: "substitute_response",
        ROLE_UNIT_HEAD: "unit_head_review",
        ROLE_ESTABLISHMENT: "establishment_routing",
        ROLE_SANCTIONING_AUTHORITY: "final_sanction",
        ROLE_DIRECTOR_SELF: "final_sanction",
    }
    return tuple(mapping[s.role] for s in route.steps)


def step_actor(role: str) -> str:
    """The actor vocabulary entry for a route role."""
    return {
        ROLE_UNIT_HEAD: ACTOR_UNIT_HEAD,
        ROLE_ESTABLISHMENT: ACTOR_ESTABLISHMENT,
        ROLE_SANCTIONING_AUTHORITY: ACTOR_SANCTIONING,
        ROLE_DIRECTOR_SELF: ACTOR_SANCTIONING,
        ROLE_SUBSTITUTE: ACTOR_EMPLOYEE,
    }[role]
