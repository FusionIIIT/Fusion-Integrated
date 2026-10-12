"""The leave state machine (Workflow Specification v1.6 state-transition tables).

Four composite workflows are transcribed exactly as their STT tables present
them (`06_ELM_Workflow_Specifications_v1.6_FINAL.docx`):

* ``CW-EL-01`` new leave processing and pending withdrawal
* ``CW-EL-02`` approved leave cancellation
* ``CW-EL-03`` ongoing leave extension
* ``CW-EL-04`` resumption review

``XTP-EL-01`` (cross-cutting SLA routing/responsibility escalation) is a
one-row System state-transition *pattern* in WF §6, not a numbered Basis or
Composite workflow: it re-routes an actionable task's responsibility without
moving the business state. ELM therefore does not model it as a request-state
transition and it is not part of the composite transitions below.

Actor kinds are the WF "Primary Actor" names. Permission mapping is
deliberately absent: the permission vocabulary is unresolved (blueprint
§3.8 #9), so a transition carries only its event and business-rule citation.

Pure Python, like ``modules/placement/domain/state_machine.py``; no DB, no
framework.
"""
from __future__ import annotations

from dataclasses import dataclass

# -- Actors (WF v1.6 "Primary Actor" column) ----------------------------------
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTIONING_AUTHORITY = "sanctioning_authority"
DIRECTOR = "director"

# -- Workflows ----------------------------------------------------------------
NEW_LEAVE = "CW-EL-01"
CANCELLATION = "CW-EL-02"
EXTENSION = "CW-EL-03"
RESUMPTION = "CW-EL-04"

# -- CW-EL-01 states ----------------------------------------------------------
DRAFT = "draft"
AWAITING_SUBSTITUTE_RESPONSE = "awaiting_substitute_response"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD_REVIEW = "awaiting_unit_head_review"
AWAITING_ESTABLISHMENT_ROUTING = "awaiting_establishment_routing"
AWAITING_FINAL_SANCTION_DECISION = "awaiting_final_sanction_decision"
AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

NEW_LEAVE_STATES = (
    DRAFT, AWAITING_SUBSTITUTE_RESPONSE, APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD_REVIEW, AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_FINAL_SANCTION_DECISION, AWAITING_DIRECTOR_SELF_SANCTION,
    APPROVED, REJECTED, WITHDRAWN,
)

#: BR-EL-022/034 — the pending states a request may be withdrawn from.
NEW_LEAVE_WITHDRAWABLE = (
    AWAITING_SUBSTITUTE_RESPONSE, APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD_REVIEW, AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_FINAL_SANCTION_DECISION, AWAITING_DIRECTOR_SELF_SANCTION,
)

# -- CW-EL-02 states ----------------------------------------------------------
APPROVED_NOT_STARTED = "approved_not_started"
CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
CANCELLATION_PENDING_FINAL = "cancellation_pending_final"
CANCELLED = "cancelled"
APPROVED_UNCHANGED = "approved_unchanged"

CANCELLATION_STATES = (
    APPROVED_NOT_STARTED, CANCELLATION_PENDING_UNIT_HEAD,
    CANCELLATION_PENDING_ESTABLISHMENT, CANCELLATION_PENDING_FINAL,
    CANCELLED, APPROVED_UNCHANGED,
)

# -- CW-EL-03 states ----------------------------------------------------------
ONGOING = "ongoing"
AWAITING_EXTENSION_SUBSTITUTE_RESPONSE = "awaiting_extension_substitute_response"
EXTENSION_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
AWAITING_EXTENSION_UNIT_HEAD_REVIEW = "awaiting_extension_unit_head_review"
EXTENSION_PENDING_ESTABLISHMENT = "extension_pending_establishment"
EXTENSION_PENDING_FINAL = "extension_pending_final"
EXTENDED_INCREMENTAL_POSTED = "extended_incremental_posted"
ORIGINAL_ONGOING_UNCHANGED = "original_ongoing_unchanged"
EXTENSION_WITHDRAWN_ORIGINAL_UNCHANGED = "extension_withdrawn_original_unchanged"

EXTENSION_STATES = (
    ONGOING, AWAITING_EXTENSION_SUBSTITUTE_RESPONSE,
    EXTENSION_APPLICANT_ACTION_REQUIRED, AWAITING_EXTENSION_UNIT_HEAD_REVIEW,
    EXTENSION_PENDING_ESTABLISHMENT, EXTENSION_PENDING_FINAL,
    EXTENDED_INCREMENTAL_POSTED, ORIGINAL_ONGOING_UNCHANGED,
    EXTENSION_WITHDRAWN_ORIGINAL_UNCHANGED,
)

#: The "{extension pending states}" the CW-EL-03 withdrawal row covers.
EXTENSION_WITHDRAWABLE = (
    AWAITING_EXTENSION_SUBSTITUTE_RESPONSE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    AWAITING_EXTENSION_UNIT_HEAD_REVIEW, EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL,
)

# -- CW-EL-04 states ----------------------------------------------------------
RETURNED = "returned"
RESUMPTION_REVIEW_PENDING = "resumption_review_pending"
NO_ADJUSTMENT = "no_adjustment"
EARLY_RETURN_SYNCHRONIZED = "early_return_synchronized"
LATE_RETURN_SYNCHRONIZED = "late_return_synchronized"

RESUMPTION_STATES = (
    RETURNED, RESUMPTION_REVIEW_PENDING, NO_ADJUSTMENT,
    EARLY_RETURN_SYNCHRONIZED, LATE_RETURN_SYNCHRONIZED,
)

STATES = {
    NEW_LEAVE: NEW_LEAVE_STATES,
    CANCELLATION: CANCELLATION_STATES,
    EXTENSION: EXTENSION_STATES,
    RESUMPTION: RESUMPTION_STATES,
}


class InvalidTransition(Exception):
    def __init__(self, workflow: str, frm: str, to: str):
        super().__init__(
            f"{workflow}: cannot move from {frm!r} to {to!r}.")
        self.workflow, self.frm, self.to = workflow, frm, to


class ActorNotAllowed(Exception):
    def __init__(self, workflow: str, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"{workflow}: a {actor_kind} may not move from {frm!r} to {to!r}.")
        self.workflow, self.actor_kind, self.frm, self.to = (
            workflow, actor_kind, frm, to)


@dataclass(frozen=True)
class Transition:
    """One legal move. ``br`` is the blueprint/STT business-rule citation."""

    workflow: str
    frm: str
    to: str
    actor: str
    event: str
    br: str = ""


def _t(workflow: str, frm: str, to: str, actor: str, event: str,
       br: str = "") -> Transition:
    return Transition(workflow, frm, to, actor, event, br)


_NEW_LEAVE: tuple[Transition, ...] = (
    _t(NEW_LEAVE, DRAFT, AWAITING_SUBSTITUTE_RESPONSE, EMPLOYEE,
       "submit; substitute required", "BR-EL-001..015, BR-EL-030..031"),
    _t(NEW_LEAVE, DRAFT, AWAITING_DIRECTOR_SELF_SANCTION, EMPLOYEE,
       "submit; no substitute; applicant is Director",
       "BR-EL-001..013, BR-EL-020, BR-EL-030..031"),
    _t(NEW_LEAVE, DRAFT, AWAITING_UNIT_HEAD_REVIEW, EMPLOYEE,
       "submit; no substitute; applicant not Director",
       "BR-EL-001..013, BR-EL-030..031"),
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE_RESPONSE, AWAITING_DIRECTOR_SELF_SANCTION,
       SUBSTITUTE, "accept; applicant is Director",
       "BR-EL-014..015, BR-EL-020"),
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE_RESPONSE, AWAITING_UNIT_HEAD_REVIEW,
       SUBSTITUTE, "accept; applicant not Director", "BR-EL-014..015"),
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE_RESPONSE, APPLICANT_ACTION_REQUIRED,
       SUBSTITUTE, "decline", "BR-EL-014..015"),
    _t(NEW_LEAVE, APPLICANT_ACTION_REQUIRED, AWAITING_SUBSTITUTE_RESPONSE,
       EMPLOYEE, "eligible replacement", "BR-EL-014..015"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD_REVIEW, APPROVED, UNIT_HEAD,
       "CL/RH approve", "BR-EL-016"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD_REVIEW, REJECTED, UNIT_HEAD,
       "CL/RH reject", "BR-EL-016"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD_REVIEW, AWAITING_ESTABLISHMENT_ROUTING,
       UNIT_HEAD,
       "higher-sanction; recommended or not recommended; Establishment configured",
       "BR-EL-017..019, BR-EL-030"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD_REVIEW, AWAITING_FINAL_SANCTION_DECISION,
       UNIT_HEAD,
       "higher-sanction; recommended or not recommended; no Establishment",
       "BR-EL-017..019, BR-EL-030"),
    _t(NEW_LEAVE, AWAITING_ESTABLISHMENT_ROUTING, AWAITING_FINAL_SANCTION_DECISION,
       ESTABLISHMENT, "routing context valid", "BR-EL-018..019, BR-EL-030"),
    _t(NEW_LEAVE, AWAITING_FINAL_SANCTION_DECISION, APPROVED,
       SANCTIONING_AUTHORITY, "approve", "BR-EL-004, BR-EL-017..019"),
    _t(NEW_LEAVE, AWAITING_FINAL_SANCTION_DECISION, REJECTED,
       SANCTIONING_AUTHORITY, "reject", "BR-EL-004, BR-EL-017..019"),
    _t(NEW_LEAVE, AWAITING_DIRECTOR_SELF_SANCTION, APPROVED, DIRECTOR,
       "approve", "BR-EL-020"),
    _t(NEW_LEAVE, AWAITING_DIRECTOR_SELF_SANCTION, REJECTED, DIRECTOR,
       "reject", "BR-EL-020"),
    *(_t(NEW_LEAVE, frm, WITHDRAWN, EMPLOYEE, "withdrawal succeeds",
         "BR-EL-022, BR-EL-034") for frm in NEW_LEAVE_WITHDRAWABLE),
)

_CANCELLATION: tuple[Transition, ...] = (
    _t(CANCELLATION, APPROVED_NOT_STARTED, CANCELLATION_PENDING_UNIT_HEAD,
       EMPLOYEE, "eligible", "BR-EL-023"),
    _t(CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD, CANCELLED, UNIT_HEAD,
       "unit-head final; approve", "BR-EL-016, BR-EL-023"),
    _t(CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD, APPROVED_UNCHANGED,
       UNIT_HEAD, "unit-head final; reject", "BR-EL-016, BR-EL-023"),
    _t(CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD,
       CANCELLATION_PENDING_ESTABLISHMENT, UNIT_HEAD,
       "higher-sanction; Establishment", "BR-EL-017..019, BR-EL-023, BR-EL-030"),
    _t(CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_FINAL,
       UNIT_HEAD, "higher-sanction; no Establishment",
       "BR-EL-017..019, BR-EL-023, BR-EL-030"),
    _t(CANCELLATION, CANCELLATION_PENDING_ESTABLISHMENT, CANCELLATION_PENDING_FINAL,
       ESTABLISHMENT, "routing valid", "BR-EL-018..019, BR-EL-023, BR-EL-030"),
    _t(CANCELLATION, CANCELLATION_PENDING_FINAL, CANCELLED,
       SANCTIONING_AUTHORITY, "approve", "BR-EL-023"),
    _t(CANCELLATION, CANCELLATION_PENDING_FINAL, APPROVED_UNCHANGED,
       SANCTIONING_AUTHORITY, "reject", "BR-EL-023"),
)

_EXTENSION: tuple[Transition, ...] = (
    _t(EXTENSION, ONGOING, AWAITING_EXTENSION_SUBSTITUTE_RESPONSE, EMPLOYEE,
       "valid; substitute required",
       "BR-EL-001, BR-EL-005..015, BR-EL-025, BR-EL-030..031"),
    _t(EXTENSION, ONGOING, AWAITING_EXTENSION_UNIT_HEAD_REVIEW, EMPLOYEE,
       "valid; no substitute",
       "BR-EL-001, BR-EL-005..013, BR-EL-025, BR-EL-030..031"),
    _t(EXTENSION, AWAITING_EXTENSION_SUBSTITUTE_RESPONSE,
       AWAITING_EXTENSION_UNIT_HEAD_REVIEW, SUBSTITUTE, "accept",
       "BR-EL-014..015, BR-EL-025"),
    _t(EXTENSION, AWAITING_EXTENSION_SUBSTITUTE_RESPONSE,
       EXTENSION_APPLICANT_ACTION_REQUIRED, SUBSTITUTE, "decline",
       "BR-EL-014..015, BR-EL-025"),
    _t(EXTENSION, EXTENSION_APPLICANT_ACTION_REQUIRED,
       AWAITING_EXTENSION_SUBSTITUTE_RESPONSE, EMPLOYEE, "eligible replacement",
       "BR-EL-014..015"),
    _t(EXTENSION, AWAITING_EXTENSION_UNIT_HEAD_REVIEW,
       EXTENSION_PENDING_ESTABLISHMENT, UNIT_HEAD,
       "recommendation; Establishment", "BR-EL-017..019, BR-EL-025, BR-EL-030"),
    _t(EXTENSION, AWAITING_EXTENSION_UNIT_HEAD_REVIEW, EXTENSION_PENDING_FINAL,
       UNIT_HEAD, "recommendation; none",
       "BR-EL-017..019, BR-EL-025, BR-EL-030"),
    _t(EXTENSION, EXTENSION_PENDING_ESTABLISHMENT, EXTENSION_PENDING_FINAL,
       ESTABLISHMENT, "routing valid", "BR-EL-018..019, BR-EL-025, BR-EL-030"),
    _t(EXTENSION, EXTENSION_PENDING_FINAL, EXTENDED_INCREMENTAL_POSTED,
       SANCTIONING_AUTHORITY, "approve", "BR-EL-025"),
    _t(EXTENSION, EXTENSION_PENDING_FINAL, ORIGINAL_ONGOING_UNCHANGED,
       SANCTIONING_AUTHORITY, "reject", "BR-EL-025"),
    *(_t(EXTENSION, frm, EXTENSION_WITHDRAWN_ORIGINAL_UNCHANGED, EMPLOYEE,
         "withdrawal succeeds", "BR-EL-022") for frm in EXTENSION_WITHDRAWABLE),
)

_RESUMPTION: tuple[Transition, ...] = (
    _t(RESUMPTION, RETURNED, RESUMPTION_REVIEW_PENDING, EMPLOYEE,
       "details submitted", "BR-EL-027"),
    _t(RESUMPTION, RESUMPTION_REVIEW_PENDING, NO_ADJUSTMENT,
       SANCTIONING_AUTHORITY, "actual = approved end", "BR-EL-027..028"),
    _t(RESUMPTION, RESUMPTION_REVIEW_PENDING, EARLY_RETURN_SYNCHRONIZED,
       SANCTIONING_AUTHORITY, "actual < approved end", "BR-EL-028"),
    _t(RESUMPTION, RESUMPTION_REVIEW_PENDING, LATE_RETURN_SYNCHRONIZED,
       SANCTIONING_AUTHORITY, "actual > approved end", "BR-EL-028"),
)

TRANSITIONS: tuple[Transition, ...] = (
    _NEW_LEAVE + _CANCELLATION + _EXTENSION + _RESUMPTION
)

_INDEX = {(t.workflow, t.frm, t.to): t for t in TRANSITIONS}


def resolve(workflow: str, frm: str, to: str,
            actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((workflow, frm, to))
    if t is None:
        raise InvalidTransition(workflow, frm, to)
    if actor_kind is not None and actor_kind != t.actor:
        raise ActorNotAllowed(workflow, actor_kind, frm, to)
    return t


def is_legal(workflow: str, frm: str, to: str) -> bool:
    return (workflow, frm, to) in _INDEX


def allowed_targets(workflow: str, frm: str,
                    actor_kind: str | None = None) -> list[str]:
    return sorted(t.to for t in TRANSITIONS
                  if t.workflow == workflow and t.frm == frm
                  and (actor_kind is None or t.actor == actor_kind))
