"""Explicit integration boundary for authoritative ELM routing data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol

from django.conf import settings

from core.api.exceptions import DomainError
from modules.elm.models import LeaveRequest

log = logging.getLogger("fusion.elm")


class ELMDependencyUnavailable(DomainError):
    code = "elm_dependency_unavailable"
    status_code = 503
    message = "A required authoritative ELM service is not available."


@dataclass(frozen=True)
class RouteStep:
    """One resolved, ordered review or sanction step."""

    role_code: str
    assigned_user_id: int


@dataclass(frozen=True)
class SubmissionRoute:
    """Route result from the configured authoritative hierarchy service."""

    steps: tuple[RouteStep, ...]
    requires_substitute: bool = False


class SubmissionRoutingResolver(Protocol):
    def resolve_route(
        self, *, applicant, leave_type: str, start_date, end_date
    ) -> SubmissionRoute: ...


_ROUTE_STATUS = {
    "UNIT_HEAD": LeaveRequest.Status.PENDING_UNIT_HEAD,
    "ESTABLISHMENT": LeaveRequest.Status.PENDING_ESTABLISHMENT,
    "SANCTIONING_AUTHORITY": LeaveRequest.Status.PENDING_FINAL_DECISION,
    "DIRECTOR_SELF_SANCTION": LeaveRequest.Status.PENDING_DIRECTOR_SANCTION,
}
_ROUTE_ROLES = frozenset(_ROUTE_STATUS)


def _configured(setting_name: str, override=None):
    configured = override if override is not None else getattr(settings, setting_name, None)
    if not configured:
        raise ELMDependencyUnavailable(f"ELM requires a configured {setting_name} integration.")
    if isinstance(configured, str):
        module_name, _, attr = configured.rpartition(".")
        if not module_name:
            raise ELMDependencyUnavailable(f"{setting_name} must be a dotted Python path.")
        try:
            configured = getattr(import_module(module_name), attr)
        except (ImportError, AttributeError) as exc:
            raise ELMDependencyUnavailable(
                f"The configured {setting_name} integration cannot be loaded."
            ) from exc
    if isinstance(configured, type):
        configured = configured()
    return configured


def get_balance_provider(override=None):
    provider = _configured("ELM_BALANCE_PROVIDER", override)
    if not callable(getattr(provider, "get_available_balance", None)):
        raise ELMDependencyUnavailable(
            "The configured ELM balance provider does not implement get_available_balance."
        )
    return provider


def get_vacation_calendar(override=None):
    calendar = _configured("ELM_VL_CALENDAR_PROVIDER", override)
    if not callable(getattr(calendar, "is_vacation_period", None)):
        raise ELMDependencyUnavailable(
            "The configured Academic Calendar adapter does not implement is_vacation_period."
        )
    return calendar


def resolve_submission_route(
    *, applicant, leave_type: str, start_date, end_date, resolver=None
) -> SubmissionRoute:
    resolver = _configured("ELM_SUBMISSION_ROUTING_RESOLVER", resolver)
    method = getattr(resolver, "resolve_route", None)
    if not callable(method):
        raise ELMDependencyUnavailable(
            "The configured ELM routing resolver does not implement resolve_route."
        )
    try:
        route = method(
            applicant=applicant,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
        )
    except ELMDependencyUnavailable:
        raise
    except Exception as exc:
        log.warning("elm.routing_resolver_failed error_type=%s", type(exc).__name__)
        raise ELMDependencyUnavailable(
            "The authoritative ELM hierarchy could not resolve this request."
        ) from exc

    if (
        not isinstance(route, SubmissionRoute)
        or not route.steps
        or not isinstance(route.requires_substitute, bool)
        or not isinstance(route.steps, tuple)
        or any(not isinstance(step, RouteStep) for step in route.steps)
    ):
        raise ELMDependencyUnavailable(
            "The authoritative ELM hierarchy returned no unambiguous route."
        )
    if any(
        step.role_code not in _ROUTE_ROLES
        or not isinstance(step.assigned_user_id, int)
        or isinstance(step.assigned_user_id, bool)
        or step.assigned_user_id <= 0
        for step in route.steps
    ):
        raise ELMDependencyUnavailable(
            "The authoritative ELM hierarchy returned an invalid route step."
        )

    role_codes = [step.role_code for step in route.steps]
    if leave_type in {"CL", "RH"}:
        valid = role_codes in (["UNIT_HEAD"], ["DIRECTOR_SELF_SANCTION"])
    else:
        valid = role_codes == ["DIRECTOR_SELF_SANCTION"] or (
            role_codes[0] == "UNIT_HEAD"
            and len(role_codes) in {2, 3}
            and role_codes[-1] == "SANCTIONING_AUTHORITY"
            and (len(role_codes) == 2 or role_codes[1] == "ESTABLISHMENT")
        )
    if not valid:
        raise ELMDependencyUnavailable(
            "The authoritative ELM hierarchy returned a route inconsistent "
            "with the configured leave-category workflow."
        )

    if any(
        (step.role_code == "DIRECTOR_SELF_SANCTION") != (step.assigned_user_id == applicant.user_id)
        for step in route.steps
    ):
        raise ELMDependencyUnavailable(
            "The authoritative ELM route has an invalid applicant assignment."
        )
    return route


def initial_request_status(route: SubmissionRoute) -> str:
    if route.requires_substitute:
        return LeaveRequest.Status.PENDING_SUBSTITUTE
    try:
        return _ROUTE_STATUS[route.steps[0].role_code]
    except (IndexError, KeyError) as exc:
        raise ELMDependencyUnavailable(
            "The ELM route has no supported initial processing step."
        ) from exc


def next_step_status(role_code: str) -> str:
    try:
        return _ROUTE_STATUS[role_code]
    except KeyError as exc:
        raise ELMDependencyUnavailable(
            "The ELM route contains an unsupported processing step."
        ) from exc
