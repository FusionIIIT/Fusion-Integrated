"""Declarative state machine for Employee Leave Management.

Pure Python — no framework imports.
Encodes the 46 transitions across CW-EL-01, CW-EL-02, CW-EL-03, and CW-EL-04.
"""

from dataclasses import dataclass
from typing import Any

from modules.leave.domain.constants import Event, RequestStatus
from modules.leave.domain.exceptions import InvalidStateTransitionError, UnauthorizedActionError


@dataclass(frozen=True)
class TransitionKey:
    from_state: RequestStatus
    event: Event


@dataclass(frozen=True)
class Transition:
    to_state: RequestStatus
    allowed_roles: tuple[str, ...]
    workflow_id: str
    cfr_citations: tuple[str, ...]
    br_citations: tuple[str, ...]
    description: str


# Pending states from which an applicant can immediately withdraw
PENDING_APPLICATION_STATES = (
    RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
    RequestStatus.APPLICANT_ACTION_REQUIRED,
    RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
    RequestStatus.AWAITING_ESTABLISHMENT_ROUTING,
    RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
    RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION,
)

PENDING_EXTENSION_STATES = (
    RequestStatus.EXT_AWAITING_SUBSTITUTE,
    RequestStatus.EXT_APPLICANT_ACTION_REQUIRED,
    RequestStatus.EXT_AWAITING_UNIT_HEAD,
    RequestStatus.EXT_PENDING_ESTABLISHMENT,
    RequestStatus.EXT_PENDING_FINAL_DECISION,
)


def _build_transition_table() -> dict[TransitionKey, list[Transition]]:
    """Builds the comprehensive declarative transition table."""
    table: dict[TransitionKey, list[Transition]] = {}

    def add(from_state: RequestStatus, event: Event, transition: Transition):
        key = TransitionKey(from_state, event)
        table.setdefault(key, []).append(transition)

    # -------------------------------------------------------------
    # CW-EL-01: New Leave Processing
    # -------------------------------------------------------------
    # T01: Draft -> Awaiting Substitute
    add(
        RequestStatus.DRAFT,
        Event.SUBMIT,
        Transition(
            to_state=RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-01 / BW-EL-02",
            cfr_citations=("CFR-EL-002", "CFR-EL-011"),
            br_citations=("BR-EL-014", "BR-EL-015"),
            description="Submit with substitute requirement",
        ),
    )
    # T02: Draft -> Awaiting Director Self-Sanction
    add(
        RequestStatus.DRAFT,
        Event.SUBMIT,
        Transition(
            to_state=RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-01 / BW-EL-07",
            cfr_citations=("CFR-EL-002", "CFR-EL-015"),
            br_citations=("BR-EL-020",),
            description="Director self-sanction with no substitute",
        ),
    )
    # T03: Draft -> Awaiting Unit Head Review
    add(
        RequestStatus.DRAFT,
        Event.SUBMIT,
        Transition(
            to_state=RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-01 / BW-EL-01",
            cfr_citations=("CFR-EL-002", "CFR-EL-013"),
            br_citations=("BR-EL-016", "BR-EL-017"),
            description="Submit with no substitute requirement",
        ),
    )
    # T04: Awaiting Substitute -> Director Self Sanction
    add(
        RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
        Event.SUBSTITUTE_ACCEPT,
        Transition(
            to_state=RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION,
            allowed_roles=("substitute",),
            workflow_id="CW-EL-01 / BW-EL-08",
            cfr_citations=("CFR-EL-012", "CFR-EL-015"),
            br_citations=("BR-EL-015", "BR-EL-020"),
            description="Substitute accepts; applicant is Director",
        ),
    )
    # T05: Awaiting Substitute -> Unit Head Review
    add(
        RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
        Event.SUBSTITUTE_ACCEPT,
        Transition(
            to_state=RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
            allowed_roles=("substitute",),
            workflow_id="CW-EL-01 / BW-EL-02",
            cfr_citations=("CFR-EL-012", "CFR-EL-013"),
            br_citations=("BR-EL-015",),
            description="Substitute accepts; routes to Unit Head",
        ),
    )
    # T06: Awaiting Substitute -> Applicant Action Required
    add(
        RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
        Event.SUBSTITUTE_DECLINE,
        Transition(
            to_state=RequestStatus.APPLICANT_ACTION_REQUIRED,
            allowed_roles=("substitute",),
            workflow_id="CW-EL-01 / BW-EL-03",
            cfr_citations=("CFR-EL-012",),
            br_citations=("BR-EL-015",),
            description="Substitute declines; applicant must nominate replacement or withdraw",
        ),
    )
    # T07: Applicant Action Required -> Awaiting Substitute
    add(
        RequestStatus.APPLICANT_ACTION_REQUIRED,
        Event.NOMINATE_REPLACEMENT,
        Transition(
            to_state=RequestStatus.AWAITING_SUBSTITUTE_RESPONSE,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-01 / BW-EL-03",
            cfr_citations=("CFR-EL-011", "CFR-EL-012"),
            br_citations=("BR-EL-014", "BR-EL-015"),
            description="Replacement substitute nominated",
        ),
    )
    # T08: Unit Head -> Approved (CL/RH)
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.APPROVE,
        Transition(
            to_state=RequestStatus.APPROVED,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-01",
            cfr_citations=("CFR-EL-013",),
            br_citations=("BR-EL-016",),
            description="Unit Head approves CL or RH (final sanction)",
        ),
    )
    # T09: Unit Head -> Rejected (CL/RH)
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.REJECT,
        Transition(
            to_state=RequestStatus.REJECTED,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-01",
            cfr_citations=("CFR-EL-013",),
            br_citations=("BR-EL-016",),
            description="Unit Head rejects CL or RH (final rejection)",
        ),
    )
    # T10 & T12: Unit Head -> Establishment Routing (Higher Sanction)
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.RECOMMEND,
        Transition(
            to_state=RequestStatus.AWAITING_ESTABLISHMENT_ROUTING,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014",),
            br_citations=("BR-EL-017", "BR-EL-019"),
            description="Unit Head recommends; routes to Establishment",
        ),
    )
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.NOT_RECOMMEND,
        Transition(
            to_state=RequestStatus.AWAITING_ESTABLISHMENT_ROUTING,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014",),
            br_citations=("BR-EL-017", "BR-EL-019"),
            description="Unit Head does not recommend; continues to Establishment",
        ),
    )
    # T11 & T13: Unit Head -> Final Sanction (No Establishment configured)
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.RECOMMEND,
        Transition(
            to_state=RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014",),
            br_citations=("BR-EL-017", "BR-EL-018"),
            description="Unit Head recommends; routes directly to Sanctioning Authority",
        ),
    )
    add(
        RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
        Event.NOT_RECOMMEND,
        Transition(
            to_state=RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014",),
            br_citations=("BR-EL-017", "BR-EL-018"),
            description="Unit Head does not recommend; routes directly to Sanctioning Authority",
        ),
    )
    # T14: Establishment -> Final Sanction
    add(
        RequestStatus.AWAITING_ESTABLISHMENT_ROUTING,
        Event.ROUTE,
        Transition(
            to_state=RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
            allowed_roles=("establishment",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014",),
            br_citations=("BR-EL-018", "BR-EL-019"),
            description="Establishment verifies and routes to Sanctioning Authority",
        ),
    )
    # T15 & T16: Final Sanction -> Approved / Rejected
    add(
        RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
        Event.APPROVE,
        Transition(
            to_state=RequestStatus.APPROVED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014", "CFR-EL-016"),
            br_citations=("BR-EL-004", "BR-EL-018"),
            description="Sanctioning Authority approves leave",
        ),
    )
    add(
        RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
        Event.REJECT,
        Transition(
            to_state=RequestStatus.REJECTED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-01 / BW-EL-04",
            cfr_citations=("CFR-EL-014", "CFR-EL-016"),
            br_citations=("BR-EL-004", "BR-EL-018"),
            description="Sanctioning Authority rejects leave",
        ),
    )
    # T17 & T18: Director Self Sanction -> Approved / Rejected
    add(
        RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        Event.APPROVE,
        Transition(
            to_state=RequestStatus.APPROVED,
            allowed_roles=("director", "applicant"),
            workflow_id="CW-EL-01 / BW-EL-07",
            cfr_citations=("CFR-EL-015",),
            br_citations=("BR-EL-020",),
            description="Director approves own leave",
        ),
    )
    add(
        RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        Event.REJECT,
        Transition(
            to_state=RequestStatus.REJECTED,
            allowed_roles=("director", "applicant"),
            workflow_id="CW-EL-01 / BW-EL-07",
            cfr_citations=("CFR-EL-015",),
            br_citations=("BR-EL-020",),
            description="Director self-rejects own leave",
        ),
    )
    # T19: Cross-cutting withdrawal from all pending application states
    for st in PENDING_APPLICATION_STATES:
        add(
            st,
            Event.WITHDRAW,
            Transition(
                to_state=RequestStatus.WITHDRAWN,
                allowed_roles=("applicant",),
                workflow_id="CW-EL-01",
                cfr_citations=("CFR-EL-017",),
                br_citations=("BR-EL-022", "BR-EL-034"),
                description="Immediate withdrawal of pending leave request",
            ),
        )

    # -------------------------------------------------------------
    # CW-EL-02: Approved Leave Cancellation
    # -------------------------------------------------------------
    add(
        RequestStatus.APPROVED,
        Event.REQUEST_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-02 / BW-EL-10",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-023",),
            description="Request cancellation of approved leave before start date",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
        Event.APPROVE_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLED,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-02 / BW-EL-10",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-016", "BR-EL-023"),
            description="Unit Head approves cancellation (CL/RH); balance restored",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
        Event.REJECT_CANCELLATION,
        Transition(
            to_state=RequestStatus.APPROVED,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-02 / BW-EL-10",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-016", "BR-EL-023"),
            description="Unit Head rejects cancellation (CL/RH); original leave stands",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
        Event.RECOMMEND_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLATION_PENDING_ESTABLISHMENT,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-02 / BW-EL-11",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-017", "BR-EL-023"),
            description="Unit Head recommends cancellation; routes to Establishment",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
        Event.RECOMMEND_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLATION_PENDING_FINAL_DECISION,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-02 / BW-EL-11",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-017", "BR-EL-023"),
            description="Unit Head recommends cancellation; routes to Sanctioning Authority",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_ESTABLISHMENT,
        Event.ROUTE_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLATION_PENDING_FINAL_DECISION,
            allowed_roles=("establishment",),
            workflow_id="CW-EL-02 / BW-EL-11",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-018", "BR-EL-023"),
            description="Establishment verifies cancellation and routes to Sanctioning Authority",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_FINAL_DECISION,
        Event.APPROVE_CANCELLATION,
        Transition(
            to_state=RequestStatus.CANCELLED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-02 / BW-EL-11",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-023",),
            description="Sanctioning Authority approves cancellation; balance restored",
        ),
    )
    add(
        RequestStatus.CANCELLATION_PENDING_FINAL_DECISION,
        Event.REJECT_CANCELLATION,
        Transition(
            to_state=RequestStatus.APPROVED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-02 / BW-EL-11",
            cfr_citations=("CFR-EL-019",),
            br_citations=("BR-EL-023",),
            description="Sanctioning Authority rejects cancellation; original leave stands",
        ),
    )

    # -------------------------------------------------------------
    # CW-EL-03: Ongoing Leave Extension
    # -------------------------------------------------------------
    add(
        RequestStatus.APPROVED,
        Event.REQUEST_EXTENSION,
        Transition(
            to_state=RequestStatus.EXT_AWAITING_SUBSTITUTE,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-03 / BW-EL-13",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-014", "BR-EL-025"),
            description="Extension requested with substitute coverage",
        ),
    )
    add(
        RequestStatus.APPROVED,
        Event.REQUEST_EXTENSION,
        Transition(
            to_state=RequestStatus.EXT_AWAITING_UNIT_HEAD,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-025",),
            description="Extension requested with no substitute coverage",
        ),
    )
    add(
        RequestStatus.EXT_AWAITING_SUBSTITUTE,
        Event.SUBSTITUTE_ACCEPT,
        Transition(
            to_state=RequestStatus.EXT_AWAITING_UNIT_HEAD,
            allowed_roles=("substitute",),
            workflow_id="CW-EL-03 / BW-EL-13",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-015", "BR-EL-025"),
            description="Extension substitute accepts",
        ),
    )
    add(
        RequestStatus.EXT_AWAITING_SUBSTITUTE,
        Event.SUBSTITUTE_DECLINE,
        Transition(
            to_state=RequestStatus.EXT_APPLICANT_ACTION_REQUIRED,
            allowed_roles=("substitute",),
            workflow_id="CW-EL-03 / BW-EL-14",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-015", "BR-EL-025"),
            description="Extension substitute declines",
        ),
    )
    add(
        RequestStatus.EXT_APPLICANT_ACTION_REQUIRED,
        Event.NOMINATE_REPLACEMENT,
        Transition(
            to_state=RequestStatus.EXT_AWAITING_SUBSTITUTE,
            allowed_roles=("applicant",),
            workflow_id="CW-EL-03 / BW-EL-14",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-014", "BR-EL-015"),
            description="Replacement substitute nominated for extension",
        ),
    )
    add(
        RequestStatus.EXT_AWAITING_UNIT_HEAD,
        Event.RECOMMEND,
        Transition(
            to_state=RequestStatus.EXT_PENDING_ESTABLISHMENT,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-017", "BR-EL-025"),
            description="Unit Head recommends extension; routes to Establishment",
        ),
    )
    add(
        RequestStatus.EXT_AWAITING_UNIT_HEAD,
        Event.RECOMMEND,
        Transition(
            to_state=RequestStatus.EXT_PENDING_FINAL_DECISION,
            allowed_roles=("unit_head",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-017", "BR-EL-025"),
            description="Unit Head recommends extension; routes to Sanctioning Authority",
        ),
    )
    add(
        RequestStatus.EXT_PENDING_ESTABLISHMENT,
        Event.ROUTE,
        Transition(
            to_state=RequestStatus.EXT_PENDING_FINAL_DECISION,
            allowed_roles=("establishment",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-018", "BR-EL-025"),
            description="Establishment verifies extension routing",
        ),
    )
    add(
        RequestStatus.EXT_PENDING_FINAL_DECISION,
        Event.APPROVE,
        Transition(
            to_state=RequestStatus.EXTENDED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-025",),
            description="Sanctioning Authority approves extension; incremental days posted",
        ),
    )
    add(
        RequestStatus.EXT_PENDING_FINAL_DECISION,
        Event.REJECT,
        Transition(
            to_state=RequestStatus.EXTENSION_REJECTED,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-03 / BW-EL-12",
            cfr_citations=("CFR-EL-020",),
            br_citations=("BR-EL-025",),
            description="Sanctioning Authority rejects extension; original ongoing leave stands",
        ),
    )
    for ext_st in PENDING_EXTENSION_STATES:
        add(
            ext_st,
            Event.WITHDRAW,
            Transition(
                to_state=RequestStatus.EXTENSION_WITHDRAWN,
                allowed_roles=("applicant",),
                workflow_id="CW-EL-03",
                cfr_citations=("CFR-EL-017", "CFR-EL-020"),
                br_citations=("BR-EL-022", "BR-EL-025"),
                description="Withdraw pending leave extension",
            ),
        )

    # -------------------------------------------------------------
    # CW-EL-04: Resumption Review
    # -------------------------------------------------------------
    for base_st in (RequestStatus.APPROVED, RequestStatus.EXTENDED):
        add(
            base_st,
            Event.SUBMIT_RESUMPTION,
            Transition(
                to_state=RequestStatus.RESUMPTION_REVIEW_PENDING,
                allowed_roles=("applicant",),
                workflow_id="CW-EL-04 / BW-EL-15",
                cfr_citations=("CFR-EL-021",),
                br_citations=("BR-EL-027",),
                description="Submit resumption of duty after returning from leave",
            ),
        )
    add(
        RequestStatus.RESUMPTION_REVIEW_PENDING,
        Event.REVIEW_NORMAL,
        Transition(
            to_state=RequestStatus.RESUMPTION_REVIEWED_NORMAL,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-04 / BW-EL-15",
            cfr_citations=("CFR-EL-021",),
            br_citations=("BR-EL-027", "BR-EL-028"),
            description="Resumption reviewed: normal return on approved end date",
        ),
    )
    add(
        RequestStatus.RESUMPTION_REVIEW_PENDING,
        Event.REVIEW_EARLY,
        Transition(
            to_state=RequestStatus.RESUMPTION_REVIEWED_EARLY,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-04 / BW-EL-16",
            cfr_citations=("CFR-EL-021",),
            br_citations=("BR-EL-028",),
            description="Resumption reviewed: early return; unavailed balance restored",
        ),
    )
    add(
        RequestStatus.RESUMPTION_REVIEW_PENDING,
        Event.REVIEW_LATE,
        Transition(
            to_state=RequestStatus.RESUMPTION_REVIEWED_LATE,
            allowed_roles=("sanctioning_authority",),
            workflow_id="CW-EL-04 / BW-EL-17",
            cfr_citations=("CFR-EL-021",),
            br_citations=("BR-EL-028",),
            description="Resumption reviewed: late return; extra days debited",
        ),
    )

    return table


TRANSITION_TABLE = _build_transition_table()


def resolve_transition(
    current_state: RequestStatus,
    event: Event,
    actor_role: str,
    context: dict[str, Any] | None = None,
) -> Transition:
    """Resolves and validates a state transition against the authoritative transition table.

    Raises:
        InvalidStateTransitionError: If no transition exists for (current_state, event).
        UnauthorizedActionError: If actor_role is not permitted for the transition.
    """
    key = TransitionKey(current_state, event)
    transitions = TRANSITION_TABLE.get(key)
    if not transitions:
        raise InvalidStateTransitionError(
            f"Event '{event}' is not permissible from current state '{current_state}'."
        )

    ctx = context or {}
    matched: Transition | None = None

    for t in transitions:
        # Check guard conditions based on context
        if event == Event.SUBMIT:
            needs_substitute = ctx.get("needs_substitute", False)
            is_director = ctx.get("is_director", False)
            if needs_substitute and t.to_state == RequestStatus.AWAITING_SUBSTITUTE_RESPONSE:
                matched = t
                break
            if (
                not needs_substitute
                and is_director
                and t.to_state == RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION
            ):
                matched = t
                break
            if (
                not needs_substitute
                and not is_director
                and t.to_state == RequestStatus.AWAITING_UNIT_HEAD_REVIEW
            ):
                matched = t
                break
        elif event == Event.SUBSTITUTE_ACCEPT:
            is_director = ctx.get("is_director", False)
            if is_director and t.to_state == RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION:
                matched = t
                break
            if not is_director and t.to_state == RequestStatus.AWAITING_UNIT_HEAD_REVIEW:
                matched = t
                break
        elif event in (Event.RECOMMEND, Event.NOT_RECOMMEND):
            establishment_enabled = ctx.get("establishment_enabled", False)
            if establishment_enabled and "ESTABLISHMENT" in t.to_state:
                matched = t
                break
            if not establishment_enabled and "FINAL_DECISION" in t.to_state:
                matched = t
                break
        elif event == Event.RECOMMEND_CANCELLATION:
            establishment_enabled = ctx.get("establishment_enabled", False)
            if (
                establishment_enabled
                and t.to_state == RequestStatus.CANCELLATION_PENDING_ESTABLISHMENT
            ):
                matched = t
                break
            if (
                not establishment_enabled
                and t.to_state == RequestStatus.CANCELLATION_PENDING_FINAL_DECISION
            ):
                matched = t
                break
        elif event == Event.REQUEST_EXTENSION:
            needs_substitute = ctx.get("needs_substitute", False)
            if needs_substitute and t.to_state == RequestStatus.EXT_AWAITING_SUBSTITUTE:
                matched = t
                break
            if not needs_substitute and t.to_state == RequestStatus.EXT_AWAITING_UNIT_HEAD:
                matched = t
                break
        else:
            matched = t
            break

    if not matched:
        matched = transitions[0]

    # Validate actor authorization
    if actor_role not in matched.allowed_roles:
        raise UnauthorizedActionError(
            f"Role '{actor_role}' is not authorized to trigger event "
            f"'{event}' from '{current_state}'."
        )

    return matched
