"""Declarative ELM workflow transitions derived from Workflow v1.6 STTs."""
from __future__ import annotations

from dataclasses import dataclass

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"
LEAVE_TYPES = (CL, RH, SCL, EL, COL, VL)

NEW = "new"
CANCELLATION = "cancellation"
EXTENSION = "extension"

DRAFT = "draft_not_submitted"
AWAITING_SUBSTITUTE = "awaiting_substitute_response"
APPLICANT_ACTION = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head_review"
AWAITING_ESTABLISHMENT = "awaiting_establishment_routing"
AWAITING_FINAL = "awaiting_final_sanction_decision"
AWAITING_DIRECTOR = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCEL_PENDING_UNIT = "cancellation_pending_unit_head_review"
CANCEL_PENDING_EST = "cancellation_pending_establishment"
CANCEL_PENDING_FINAL = "cancellation_pending_final_decision"
CANCELLED = "cancelled"
CANCEL_REJECTED = "cancellation_rejected_original_unchanged"
EXT_AWAITING_SUBSTITUTE = "awaiting_extension_substitute_response"
EXT_APPLICANT_ACTION = "extension_applicant_action_required"
EXT_AWAITING_UNIT = "awaiting_extension_unit_head_review"
EXT_AWAITING_EST = "extension_pending_establishment"
EXT_AWAITING_FINAL = "extension_pending_final_decision"
EXTENDED = "extended_incremental_period_posted"
EXT_REJECTED = "extension_rejected_original_unchanged"
EXT_WITHDRAWN = "extension_request_withdrawn_original_unchanged"

PENDING_STATES = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL, AWAITING_DIRECTOR,
    CANCEL_PENDING_UNIT, CANCEL_PENDING_EST, CANCEL_PENDING_FINAL,
    EXT_AWAITING_SUBSTITUTE, EXT_APPLICANT_ACTION, EXT_AWAITING_UNIT,
    EXT_AWAITING_EST, EXT_AWAITING_FINAL,
})


@dataclass(frozen=True)
class Transition:
    request_kind: str
    source: str
    event: str
    destination: str
    actor: str
    permission: str
    outcome: str = ""


TRANSITIONS: tuple[Transition, ...] = (
    Transition(NEW, DRAFT, "submit", AWAITING_SUBSTITUTE, "employee", "leave.application.create", "substitute_required"),
    Transition(NEW, DRAFT, "submit", AWAITING_UNIT_HEAD, "employee", "leave.application.create", "no_substitute_not_director"),
    Transition(NEW, DRAFT, "submit", AWAITING_DIRECTOR, "employee", "leave.application.create", "no_substitute_director"),
    Transition(NEW, AWAITING_SUBSTITUTE, "accept_substitute", AWAITING_UNIT_HEAD, "substitute", "leave.substitute.update", "not_director"),
    Transition(NEW, AWAITING_SUBSTITUTE, "accept_substitute", AWAITING_DIRECTOR, "substitute", "leave.substitute.update", "director"),
    Transition(NEW, AWAITING_SUBSTITUTE, "decline_substitute", APPLICANT_ACTION, "substitute", "leave.substitute.update"),
    Transition(NEW, APPLICANT_ACTION, "replace_substitute", AWAITING_SUBSTITUTE, "employee", "leave.application.update"),
    Transition(NEW, AWAITING_UNIT_HEAD, "unit_head_decision", APPROVED, "unit_head", "leave.application.review", "cl_rh_approve"),
    Transition(NEW, AWAITING_UNIT_HEAD, "unit_head_decision", REJECTED, "unit_head", "leave.application.review", "cl_rh_reject"),
    Transition(NEW, AWAITING_UNIT_HEAD, "unit_head_recommendation", AWAITING_ESTABLISHMENT, "unit_head", "leave.application.review", "higher_establishment"),
    Transition(NEW, AWAITING_UNIT_HEAD, "unit_head_recommendation", AWAITING_FINAL, "unit_head", "leave.application.review", "higher_direct"),
    Transition(NEW, AWAITING_ESTABLISHMENT, "route", AWAITING_FINAL, "establishment", "leave.application.review"),
    Transition(NEW, AWAITING_FINAL, "sanction", APPROVED, "sanctioning_authority", "leave.application.approve", "approve"),
    Transition(NEW, AWAITING_FINAL, "sanction", REJECTED, "sanctioning_authority", "leave.application.approve", "reject"),
    Transition(NEW, AWAITING_DIRECTOR, "director_sanction", APPROVED, "director", "leave.application.approve", "approve"),
    Transition(NEW, AWAITING_DIRECTOR, "director_sanction", REJECTED, "director", "leave.application.approve", "reject"),
    Transition(CANCELLATION, APPROVED, "request_cancellation", CANCEL_PENDING_UNIT, "employee", "leave.application.delete", "eligible"),
    Transition(CANCELLATION, CANCEL_PENDING_UNIT, "unit_head_cancel", CANCELLED, "unit_head", "leave.application.review", "unit_final_approve"),
    Transition(CANCELLATION, CANCEL_PENDING_UNIT, "unit_head_cancel", CANCEL_REJECTED, "unit_head", "leave.application.review", "unit_final_reject"),
    Transition(CANCELLATION, CANCEL_PENDING_UNIT, "unit_head_recommendation", CANCEL_PENDING_EST, "unit_head", "leave.application.review", "higher_establishment"),
    Transition(CANCELLATION, CANCEL_PENDING_UNIT, "unit_head_recommendation", CANCEL_PENDING_FINAL, "unit_head", "leave.application.review", "higher_direct"),
    Transition(CANCELLATION, CANCEL_PENDING_EST, "route", CANCEL_PENDING_FINAL, "establishment", "leave.application.review"),
    Transition(CANCELLATION, CANCEL_PENDING_FINAL, "sanction", CANCELLED, "sanctioning_authority", "leave.application.approve", "approve"),
    Transition(CANCELLATION, CANCEL_PENDING_FINAL, "sanction", CANCEL_REJECTED, "sanctioning_authority", "leave.application.approve", "reject"),
    Transition(EXTENSION, APPROVED, "request_extension", EXT_AWAITING_SUBSTITUTE, "employee", "leave.application.create", "substitute_required"),
    Transition(EXTENSION, APPROVED, "request_extension", EXT_AWAITING_UNIT, "employee", "leave.application.create", "no_substitute"),
    Transition(EXTENSION, EXT_AWAITING_SUBSTITUTE, "accept_substitute", EXT_AWAITING_UNIT, "substitute", "leave.substitute.update", "accept"),
    Transition(EXTENSION, EXT_AWAITING_SUBSTITUTE, "decline_substitute", EXT_APPLICANT_ACTION, "substitute", "leave.substitute.update", "decline"),
    Transition(EXTENSION, EXT_APPLICANT_ACTION, "replace_substitute", EXT_AWAITING_SUBSTITUTE, "employee", "leave.application.update"),
    Transition(EXTENSION, EXT_AWAITING_UNIT, "unit_head_recommendation", EXT_AWAITING_EST, "unit_head", "leave.application.review", "higher_establishment"),
    Transition(EXTENSION, EXT_AWAITING_UNIT, "unit_head_recommendation", EXT_AWAITING_FINAL, "unit_head", "leave.application.review", "higher_direct"),
    Transition(EXTENSION, EXT_AWAITING_EST, "route", EXT_AWAITING_FINAL, "establishment", "leave.application.review"),
    Transition(EXTENSION, EXT_AWAITING_FINAL, "sanction", EXTENDED, "sanctioning_authority", "leave.application.approve", "approve"),
    Transition(EXTENSION, EXT_AWAITING_FINAL, "sanction", EXT_REJECTED, "sanctioning_authority", "leave.application.approve", "reject"),
)

for source in PENDING_STATES:
    kind = EXTENSION if source.startswith("extension_") or source.startswith("awaiting_extension_") else NEW
    destination = EXT_WITHDRAWN if kind == EXTENSION else WITHDRAWN
    TRANSITIONS += (Transition(kind, source, "withdraw", destination, "employee", "leave.application.delete"),)

_INDEX = {(t.request_kind, t.source, t.event, t.outcome): t for t in TRANSITIONS}


class InvalidTransition(ValueError):
    """The requested event is not allowed from the current workflow state."""


def resolve(request_kind: str, source: str, event: str, outcome: str = "") -> Transition:
    transition = _INDEX.get((request_kind, source, event, outcome))
    if transition is None:
        transition = _INDEX.get((request_kind, source, event, ""))
    if transition is None:
        raise InvalidTransition(f"Cannot apply {event!r} to {request_kind} in {source!r}.")
    return transition


def is_pending(status: str) -> bool:
    return status in PENDING_STATES


def is_higher_sanction(leave_type: str) -> bool:
    return leave_type in {SCL, EL, COL, VL}
