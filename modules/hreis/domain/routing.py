"""Approval routing from explicit effective policy, never from guessed hierarchy.

HR-AFR-006..009 say HOD/Registrar/Director are applicable in some cases.
They do not specify a complete request-type/category decision matrix.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .workflow import FAMILIES

AUTHORITY_DESIGNATIONS = frozenset(
    {
        "HOD (CSE)",
        "HOD (Design)",
        "HOD (ECE)",
        "HOD (Liberal Arts)",
        "HOD (ME)",
        "HOD (NS)",
        "Registrar",
        "Director",
    }
)
EMPLOYEE_KINDS = frozenset({"faculty", "staff"})


class RouteError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ApprovalRoute:
    family: str
    employee_kind: str
    department: str
    version: str
    authorities: tuple[str, ...]


def validate_route(route: ApprovalRoute) -> ApprovalRoute:
    if route.family not in FAMILIES or route.employee_kind not in EMPLOYEE_KINDS:
        raise RouteError("invalid_scope", "The employee kind or request type is unsupported.")
    if (
        not isinstance(route.department, str)
        or not route.department.strip()
        or not isinstance(route.version, str)
        or not route.version.strip()
    ):
        raise RouteError("missing_scope", "Routing requires department and policy version.")
    if not route.authorities:
        raise RouteError("empty_route", "No approval authority is configured.")
    if any(actor not in AUTHORITY_DESIGNATIONS for actor in route.authorities):
        raise RouteError(
            "unknown_authority", "An approval authority is not a verified IAM designation."
        )
    if len(set(route.authorities)) != len(route.authorities):
        raise RouteError(
            "duplicate_authority", "An approval route cannot visit the same authority twice."
        )
    return route


def choose_route(
    family: str,
    employee_kind: str,
    department: str,
    policies: Mapping[tuple[str, str, str], ApprovalRoute],
) -> ApprovalRoute:
    """Require an exact configured route: never silently route to Registrar/HOD."""
    if family not in FAMILIES or employee_kind not in EMPLOYEE_KINDS:
        raise RouteError("invalid_scope", "The employee kind or request type is unsupported.")
    if not isinstance(department, str) or not department.strip():
        raise RouteError("missing_scope", "Employee department is required for approval routing.")
    route = policies.get((family, employee_kind, department))
    if route is None:
        raise RouteError(
            "policy_unavailable", "Approval routing has not been configured for this request."
        )
    if (route.family, route.employee_kind, route.department) != (family, employee_kind, department):
        raise RouteError("mismatched_policy", "The configured route does not match the request.")
    return validate_route(route)


def current_authority(route: ApprovalRoute, step: int) -> str:
    validate_route(route)
    if (
        not isinstance(step, int)
        or isinstance(step, bool)
        or not 0 <= step < len(route.authorities)
    ):
        raise RouteError("invalid_step", "The approval step is outside the configured route.")
    return route.authorities[step]


def require_current_authority(route: ApprovalRoute, step: int, acting_designation: str) -> None:
    if current_authority(route, step) != acting_designation:
        raise RouteError("wrong_authority", "Only the current assigned approval authority may act.")


def forward_step(route: ApprovalRoute, step: int, acting_designation: str) -> int:
    """One hop at a time; cannot jump to an arbitrary authority."""
    require_current_authority(route, step, acting_designation)
    if step + 1 >= len(route.authorities):
        raise RouteError("no_next_authority", "No next approval authority is configured.")
    return step + 1
