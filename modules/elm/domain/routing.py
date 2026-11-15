"""Authority resolution (BR-EL-016..020, BR-EL-030)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from modules.elm.domain import categories as c

UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTION = "sanction"
DIRECTOR = "director"


class RouteUnresolved(Exception):
    pass


class HierarchyInvalid(Exception):
    pass


@dataclass(frozen=True)
class Step:
    step: str
    role: str

    def as_dict(self) -> dict:
        return {"step": self.step, "role": self.role}


def parse_hierarchy(h: dict) -> dict:
    if not isinstance(h, dict):
        raise HierarchyInvalid("The hierarchy must be an object.")
    if not isinstance(h.get("unit_heads"), dict):
        raise HierarchyInvalid("The hierarchy needs a unit_heads mapping.")
    sanctioning = h.get("sanctioning")
    if not isinstance(sanctioning, dict):
        raise HierarchyInvalid("The hierarchy needs a sanctioning mapping.")
    for kind in c.EMPLOYEE_KINDS:
        if not (sanctioning.get(kind) or {}).get("default"):
            raise HierarchyInvalid(f"No default sanctioning authority for {kind}.")
    if not h.get("director_role"):
        raise HierarchyInvalid("The hierarchy must name the Director's designation.")
    return h


def roles_in(h: dict) -> set[str]:
    out = set(h["unit_heads"].values()) | {h["director_role"]}
    if h.get("establishment_role"):
        out.add(h["establishment_role"])
    for per_kind in h["sanctioning"].values():
        out |= {v for v in per_kind.values() if v}
    return out


def sanctioning_role(h: dict, kind: str, category: str) -> str:
    per_kind = h["sanctioning"].get(kind) or {}
    role = per_kind.get(category) or per_kind.get("default")
    if not role:
        raise RouteUnresolved(
            f"No sanctioning authority is configured for {kind} {category}.")
    return role


def unit_head_role(h: dict, unit: str) -> str:
    role = h["unit_heads"].get(unit or "")
    if not role:
        raise RouteUnresolved(
            f"No Unit Head is configured for your unit "
            f"({unit or 'not recorded'}). Ask the Leave Administrator to publish one.")
    return role


def resolve_route(*, category: str, kind: str, unit: str,
                  applicant_roles: Iterable[str], hierarchy: dict) -> list[Step]:
    director = hierarchy["director_role"]
    if director in set(applicant_roles):
        return [Step(DIRECTOR, director)]
    head = Step(UNIT_HEAD, unit_head_role(hierarchy, unit))
    if category in c.UNIT_HEAD_FINAL:
        return [head]
    steps = [head]
    estt = hierarchy.get("establishment_role")
    estt_cats = hierarchy.get("establishment_categories") or list(c.HIGHER_SANCTION)
    if estt and category in estt_cats:
        steps.append(Step(ESTABLISHMENT, estt))
    steps.append(Step(SANCTION, sanctioning_role(hierarchy, kind, category)))
    return steps


def resumption_verifier(route: list[dict], hierarchy: dict) -> str:
    configured = hierarchy.get("resumption_verifier") or UNIT_HEAD
    if configured == UNIT_HEAD:
        for s in route:
            if s["step"] in (UNIT_HEAD, DIRECTOR):
                return s["role"]
    if configured == ESTABLISHMENT and hierarchy.get("establishment_role"):
        return hierarchy["establishment_role"]
    return route[0]["role"]
