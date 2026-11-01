from dataclasses import dataclass

SCHOLARSHIP_APPLICATION = "scholarship_application"
SCHOLARSHIP_RENEWAL = "scholarship_renewal"
CONVOCATION_AWARD_CYCLE = "convocation_award_cycle"


@dataclass(frozen=True)
class Transition:
    workflow_key: str
    frm: str
    to: str
    actor: str
    guard: str


class InvalidTransition(Exception):
    pass


class ActorNotAllowed(Exception):
    pass


class AmbiguousTransition(Exception):
    pass


SCHOLARSHIP_APPLICATION_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Not Started / Draft",
        "Submitted",
        "Student",
        "Submission passes eligibility, duplicate and completeness checks",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Submitted",
        "Under Verification",
        "SPACS Assistant",
        "Assistant opens assigned verification",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Verification",
        "Verified / Routed for Decision",
        "SPACS Assistant",
        "Verification satisfied",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Verification",
        "Correction Required",
        "SPACS Assistant",
        "Correction required",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Correction Required",
        "Resubmitted",
        "Student",
        "Resubmission passes completeness checks",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Resubmitted",
        "Verified / Routed for Decision",
        "SPACS Assistant",
        "Reverification satisfied",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Verification",
        "Verified / Routed for Decision",
        "SPACS Assistant",
        "Verification satisfied without correction",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Verification",
        "Verification Concern / Routed",
        "SPACS Assistant",
        "Unresolved concern requiring decision",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Verified / Routed for Decision",
        "Under Convener Review",
        "SPACS Convener",
        "Open decision task",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Verification Concern / Routed",
        "Under Convener Review",
        "SPACS Convener",
        "Open decision task",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Convener Review",
        "Approved",
        "SPACS Convener",
        "Approve",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Convener Review",
        "Rejected",
        "SPACS Convener",
        "Reject",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Convener Review",
        "Correction Required",
        "SPACS Convener",
        "Return for correction",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Submitted",
        "Withdrawn",
        "Student",
        "State is configured withdrawable; no final decision",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Under Verification",
        "Withdrawn",
        "Student",
        "State is configured withdrawable and not locked by policy",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Correction Required",
        "Withdrawn",
        "Student",
        "State is configured withdrawable",
    ),
    Transition(
        SCHOLARSHIP_APPLICATION,
        "Verified / Routed for Decision",
        "Withdrawn",
        "Student",
        "Allowed only if Convener review has not begun and scheme marks state withdrawable",
    ),
)


SCHOLARSHIP_RENEWAL_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Awarded / Renewal Eligible",
        "Renewal Submitted",
        "Student",
        "Renewal window open; valid submission",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Submitted",
        "Renewal Under Verification",
        "SPACS Assistant",
        "Open task",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Under Verification",
        "Correction Required",
        "SPACS Assistant",
        "Correction required",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Correction Required",
        "Renewal Resubmitted",
        "Student",
        "Valid renewal resubmission",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Resubmitted",
        "Renewal Verified / Routed",
        "SPACS Assistant",
        "Reverification satisfied",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Under Verification",
        "Renewal Verified / Routed",
        "SPACS Assistant",
        "Verification satisfied without correction",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Verified / Routed",
        "Renewal Under Decision",
        "SPACS Convener",
        "Open decision",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Under Decision",
        "Renewed / Approved",
        "SPACS Convener",
        "Approve",
    ),
    Transition(
        SCHOLARSHIP_RENEWAL,
        "Renewal Under Decision",
        "Renewal Rejected",
        "SPACS Convener",
        "Reject",
    ),
)


CONVOCATION_AWARD_CYCLE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Award Cycle Open",
        "Candidate Pool Prepared",
        "SPACS Convener",
        "Configured candidate-source method and criteria applied",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Candidate Pool Prepared",
        "Under Committee Evaluation",
        "Award Evaluation Committee",
        "Begin evaluation",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Under Committee Evaluation",
        "Committee Result Recorded",
        "Award Evaluation Committee",
        "Committee result recorded",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Committee Result Recorded",
        "Ready for Publication",
        "SPACS Convener",
        "Required approval evidence available",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Committee Result Recorded",
        "Awaiting Institutional Approval",
        "SPACS Convener",
        "Approval still pending",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Awaiting Institutional Approval",
        "Ready for Publication",
        "SPACS Convener",
        "Approval evidence received/recorded",
    ),
    Transition(
        CONVOCATION_AWARD_CYCLE,
        "Ready for Publication",
        "Published",
        "SPACS Convener",
        "Approved outcome confirmed",
    ),
)


ALL_TRANSITIONS = (
    *SCHOLARSHIP_APPLICATION_TRANSITIONS,
    *SCHOLARSHIP_RENEWAL_TRANSITIONS,
    *CONVOCATION_AWARD_CYCLE_TRANSITIONS,
)


def resolve(
    workflow_key: str,
    frm: str,
    to: str,
    actor: str,
    guard: str | None = None,
) -> Transition:
    edge_transitions = tuple(
        transition
        for transition in ALL_TRANSITIONS
        if (
            transition.workflow_key == workflow_key
            and transition.frm == frm
            and transition.to == to
        )
    )
    if not edge_transitions:
        raise InvalidTransition(f"No transition exists from {frm!r} to {to!r} in {workflow_key!r}.")

    actor_transitions = tuple(
        transition for transition in edge_transitions if transition.actor == actor
    )
    if not actor_transitions:
        raise ActorNotAllowed(f"{actor!r} may not move from {frm!r} to {to!r}.")

    matching_transitions = (
        tuple(transition for transition in actor_transitions if transition.guard == guard)
        if guard is not None
        else actor_transitions
    )
    if not matching_transitions:
        raise InvalidTransition(f"No transition from {frm!r} to {to!r} has guard {guard!r}.")
    if len(matching_transitions) > 1:
        raise AmbiguousTransition(f"More than one transition matches {frm!r} to {to!r}.")
    return matching_transitions[0]


def is_legal(
    workflow_key: str,
    frm: str,
    to: str,
    actor: str | None = None,
    guard: str | None = None,
) -> bool:
    if actor is None:
        matching_transitions = tuple(
            transition
            for transition in ALL_TRANSITIONS
            if (
                transition.workflow_key == workflow_key
                and transition.frm == frm
                and transition.to == to
                and (guard is None or transition.guard == guard)
            )
        )
        return bool(matching_transitions)

    try:
        resolve(workflow_key, frm, to, actor, guard)
    except (InvalidTransition, ActorNotAllowed, AmbiguousTransition):
        return False
    return True


def allowed_targets(
    workflow_key: str,
    frm: str,
    actor: str | None = None,
) -> list[str]:
    return list(
        dict.fromkeys(
            transition.to
            for transition in ALL_TRANSITIONS
            if (
                transition.workflow_key == workflow_key
                and transition.frm == frm
                and (actor is None or transition.actor == actor)
            )
        )
    )
