"""Declarative request state machine; pure Python, no Django imports."""

from dataclasses import dataclass

from modules.elm.domain.errors import ActorNotAllowed, InvalidTransition

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
UNIT_HEAD_REVIEW = "unit_head_review"
ESTABLISHMENT_REVIEW = "establishment_review"
AUTHORITY_REVIEW = "authority_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING = "cancellation_pending"
CANCELLED = "cancelled"
EXTENSION_PENDING = "extension_pending"
RESUMPTION_PENDING = "resumption_pending"
CLOSED = "closed"

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED, CLOSED})


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    actors: frozenset[str]
    permission: str


TRANSITIONS = (
    Transition(DRAFT, AWAITING_SUBSTITUTE, frozenset({"employee"}), "elm.request.create"),
    Transition(DRAFT, UNIT_HEAD_REVIEW, frozenset({"employee"}), "elm.request.create"),
    Transition(
        AWAITING_SUBSTITUTE, UNIT_HEAD_REVIEW, frozenset({"substitute"}), "elm.substitute.respond"
    ),
    Transition(
        AWAITING_SUBSTITUTE, AUTHORITY_REVIEW, frozenset({"substitute"}), "elm.substitute.respond"
    ),
    Transition(UNIT_HEAD_REVIEW, APPROVED, frozenset({"unit_head"}), "elm.request.review"),
    Transition(UNIT_HEAD_REVIEW, REJECTED, frozenset({"unit_head"}), "elm.request.review"),
    Transition(
        UNIT_HEAD_REVIEW, ESTABLISHMENT_REVIEW, frozenset({"unit_head"}), "elm.request.review"
    ),
    Transition(
        ESTABLISHMENT_REVIEW, AUTHORITY_REVIEW, frozenset({"establishment"}), "elm.request.route"
    ),
    Transition(ESTABLISHMENT_REVIEW, REJECTED, frozenset({"establishment"}), "elm.request.route"),
    Transition(AUTHORITY_REVIEW, APPROVED, frozenset({"authority"}), "elm.request.sanction"),
    Transition(AUTHORITY_REVIEW, REJECTED, frozenset({"authority"}), "elm.request.sanction"),
    Transition(DRAFT, WITHDRAWN, frozenset({"employee"}), "elm.request.withdraw"),
    Transition(AWAITING_SUBSTITUTE, WITHDRAWN, frozenset({"employee"}), "elm.request.withdraw"),
    Transition(UNIT_HEAD_REVIEW, WITHDRAWN, frozenset({"employee"}), "elm.request.withdraw"),
    Transition(ESTABLISHMENT_REVIEW, WITHDRAWN, frozenset({"employee"}), "elm.request.withdraw"),
    Transition(AUTHORITY_REVIEW, WITHDRAWN, frozenset({"employee"}), "elm.request.withdraw"),
    Transition(APPROVED, CANCELLATION_PENDING, frozenset({"employee"}), "elm.request.cancel"),
    Transition(
        CANCELLATION_PENDING, CANCELLED, frozenset({"authority"}), "elm.request.cancel_review"
    ),
    Transition(
        CANCELLATION_PENDING, REJECTED, frozenset({"authority"}), "elm.request.cancel_review"
    ),
    Transition(APPROVED, EXTENSION_PENDING, frozenset({"employee"}), "elm.request.extend"),
    Transition(APPROVED, RESUMPTION_PENDING, frozenset({"employee"}), "elm.request.resume"),
    Transition(
        RESUMPTION_PENDING,
        CLOSED,
        frozenset({"unit_head", "establishment"}),
        "elm.request.verify_resume",
    ),
)


def resolve(source: str, target: str, actor: str) -> Transition:
    for transition in TRANSITIONS:
        if transition.source == source and transition.target == target:
            if actor not in transition.actors:
                raise ActorNotAllowed(f"Actor {actor!r} cannot perform {source} -> {target}.")
            return transition
    raise InvalidTransition(f"Transition {source!r} -> {target!r} is not allowed.")


def allowed_targets(source: str, actor: str | None = None) -> tuple[str, ...]:
    return tuple(
        t.target for t in TRANSITIONS if t.source == source and (actor is None or actor in t.actors)
    )
