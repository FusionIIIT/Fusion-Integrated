"""Authoritative IAA workflow transitions from IAA workflow specification v1.3.

This module is deliberately framework-free. Services must validate every state
change here before writing it.
"""
from __future__ import annotations

from dataclasses import dataclass


BASIC_USER = "Basic User"
FINANCE = "Finance Staff"
HOD = "HoD"
DEAN = "Dean"
DIRECTOR = "Director"
AUDITOR = "Auditor"
ADMIN = "System Admin"
SYSTEM = "System"
AUTHORITIES = frozenset({HOD, DEAN, DIRECTOR})


class InvalidTransition(ValueError):
    pass


class ActorNotAllowed(PermissionError):
    pass


class GuardFailed(ValueError):
    pass


@dataclass(frozen=True)
class Transition:
    source: str
    destination: str
    actors: frozenset[str]
    guard: str = ""


def _t(source: str, destination: str, *actors: str, guard: str = "") -> Transition:
    return Transition(source, destination, frozenset(actors), guard)


REQUEST_TRANSITIONS = (
    _t("Draft", "Submitted", BASIC_USER, guard="submission_complete"),
    _t("Submitted", "Query Raised", FINANCE, guard="clarification_details_required"),
    _t("Submitted", "Finance Validated", FINANCE, guard="validation_passed"),
    _t("Query Raised", "Query Responded", BASIC_USER, guard="response_complete"),
    _t("Query Responded", "Query Raised", FINANCE, guard="clarification_details_required"),
    _t("Query Responded", "Finance Validated", FINANCE, guard="validation_passed"),
    _t("Finance Validated", "Approval Pending", *AUTHORITIES,
       guard="another_approval_level"),
    _t("Finance Validated", "Approved", *AUTHORITIES, guard="final_approval"),
    _t("Finance Validated", "Rejected", *AUTHORITIES, guard="remarks_required"),
    _t("Approval Pending", "Approval Pending", *AUTHORITIES,
       guard="another_approval_level"),
    _t("Approval Pending", "Approved", *AUTHORITIES, guard="final_approval"),
    _t("Approval Pending", "Rejected", *AUTHORITIES, guard="remarks_required"),
    _t("Finance Validated", "Escalated", SYSTEM, guard="approval_overdue"),
    _t("Approval Pending", "Escalated", SYSTEM, guard="approval_overdue"),
    _t("Escalated", "Approval Pending", *AUTHORITIES,
       guard="another_approval_level"),
    _t("Escalated", "Approved", *AUTHORITIES, guard="final_approval"),
    _t("Escalated", "Rejected", *AUTHORITIES, guard="remarks_required"),
    _t("Approved", "Recorded", FINANCE, guard="internal_processing_complete"),
)

TA_TRANSITIONS = (
    _t("Submitted", "Query Raised", FINANCE, guard="clarification_details_required"),
    _t("Submitted", "Verified", FINANCE, guard="verification_passed_no_approval"),
    _t("Submitted", "Approval Pending", FINANCE,
       guard="verification_passed_approval_required"),
    _t("Submitted", "Rejected", FINANCE, guard="policy_verification_failed"),
    _t("Query Raised", "Query Responded", BASIC_USER, guard="response_complete"),
    _t("Query Responded", "Query Raised", FINANCE, guard="clarification_details_required"),
    _t("Query Responded", "Verified", FINANCE, guard="verification_passed_no_approval"),
    _t("Query Responded", "Approval Pending", FINANCE,
       guard="verification_passed_approval_required"),
    _t("Query Responded", "Rejected", FINANCE, guard="policy_verification_failed"),
    _t("Approval Pending", "Approval Pending", *AUTHORITIES,
       guard="another_approval_level"),
    _t("Approval Pending", "Approved", *AUTHORITIES, guard="final_approval"),
    _t("Approval Pending", "Rejected", *AUTHORITIES, guard="remarks_required"),
    _t("Approval Pending", "Escalated", SYSTEM, guard="approval_overdue"),
    _t("Escalated", "Approval Pending", *AUTHORITIES,
       guard="another_approval_level"),
    _t("Escalated", "Approved", *AUTHORITIES, guard="final_approval"),
    _t("Escalated", "Rejected", *AUTHORITIES, guard="remarks_required"),
    _t("Verified", "Recorded", FINANCE, guard="internal_processing_complete"),
    _t("Approved", "Recorded", FINANCE, guard="internal_processing_complete"),
)

ANOMALY_TRANSITIONS = (
    _t("Open", "Resolved", FINANCE, AUDITOR, HOD, DEAN, DIRECTOR,
       guard="remarks_required"),
    _t("Open", "Escalated", FINANCE, AUDITOR, HOD, DEAN, DIRECTOR,
       guard="remarks_required"),
    _t("Escalated", "Resolved", FINANCE, AUDITOR, HOD, DEAN, DIRECTOR,
       guard="remarks_required"),
)

OBSERVATION_TRANSITIONS = (
    _t("Open", "Responded", BASIC_USER, guard="response_complete"),
    _t("Responded", "Closed", AUDITOR, guard="verification_satisfactory"),
    _t("Responded", "Open", AUDITOR, guard="verification_unsatisfactory"),
)

WORKFLOWS = {
    "request": REQUEST_TRANSITIONS,
    "ta_claim": TA_TRANSITIONS,
    "anomaly": ANOMALY_TRANSITIONS,
    "observation": OBSERVATION_TRANSITIONS,
}

TERMINAL = {
    "request": frozenset({"Recorded", "Rejected"}),
    "ta_claim": frozenset({"Recorded", "Rejected"}),
    "anomaly": frozenset({"Resolved"}),
    "observation": frozenset({"Closed"}),
}


def resolve(record_type: str, source: str, destination: str,
            actor_role: str) -> Transition:
    transitions = WORKFLOWS.get(record_type)
    if transitions is None:
        raise InvalidTransition(f"Unknown IAA record type {record_type!r}.")
    matches = [t for t in transitions
               if t.source == source and t.destination == destination]
    if not matches:
        raise InvalidTransition(
            f"Cannot move {record_type} from {source!r} to {destination!r}.")
    for transition in matches:
        if actor_role in transition.actors:
            return transition
    raise ActorNotAllowed(
        f"{actor_role!r} cannot move {record_type} from {source!r} "
        f"to {destination!r}.")


def check_guard(transition: Transition, *, values: dict) -> None:
    guard = transition.guard
    if guard in {"remarks_required", "response_complete"}:
        value = values.get("remarks") if guard == "remarks_required" else values.get("response")
        if not str(value or "").strip():
            raise GuardFailed(f"{guard} is required.")
    elif guard == "clarification_details_required" and not str(values.get("remarks") or "").strip():
        raise GuardFailed("Finance clarification details are required.")
    elif guard == "verification_satisfactory" and values.get("satisfactory") is not True:
        raise GuardFailed("Auditor verification must be satisfactory to close.")
    elif guard == "verification_unsatisfactory" and values.get("satisfactory") is not False:
        raise GuardFailed("An unsatisfactory verification is required to reopen.")
    elif guard == "submission_complete" and values.get("complete") is not True:
        raise GuardFailed("Required submission fields and evidence are missing.")
    elif guard == "another_approval_level" and values.get("more_levels") is not True:
        raise GuardFailed("No further configured approval level remains.")
    elif guard == "final_approval" and values.get("more_levels") is not False:
        raise GuardFailed("A configured approval level remains.")
    elif guard == "approval_overdue" and values.get("overdue") is not True:
        raise GuardFailed("The configured approval time limit has not elapsed.")
    elif guard == "internal_processing_complete" and values.get("complete") is not True:
        raise GuardFailed("Internal processing must be confirmed before recording.")
    elif guard.startswith("validation_passed") and values.get("passed") is not True:
        raise GuardFailed("Finance validation has not passed.")
    elif guard.startswith("verification_passed") and values.get("passed") is not True:
        raise GuardFailed("TA policy verification has not passed.")
    elif guard == "policy_verification_failed" and values.get("passed") is not False:
        raise GuardFailed("Policy failure must be recorded before rejection.")


def validate_transition(record_type: str, source: str, destination: str,
                        actor_role: str, *, values: dict | None = None) -> Transition:
    transition = resolve(record_type, source, destination, actor_role)
    check_guard(transition, values=values or {})
    return transition
