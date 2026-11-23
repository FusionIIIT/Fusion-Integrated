"""Declarative finite state machines for LMS entities (BR-LMS-006, BR-LMS-010, BR-LMS-017)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from modules.lms.domain.constants import AssignmentStatus, GradeStatus, MaterialStatus


class IllegalTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, frm: str, to: str, entity: str = "entity", message: str = ""):
        msg = (
            message
            or f"Cannot move {entity} from {frm!r} to {to!r}. "
            "Check allowed lifecycle transitions or reset the entity to a valid prior state."
        )
        super().__init__(msg)
        self.frm, self.to, self.entity = frm, to, entity


class ActorNotAllowedError(IllegalTransitionError):
    """Raised when an actor lacks authority for a state transition."""

    def __init__(self, actor: str, frm: str, to: str, entity: str = "entity"):
        super().__init__(
            frm,
            to,
            entity,
            message=(
                f"Actor {actor!r} cannot move {entity} from {frm!r} to {to!r}. "
                "Request an authorized role (instructor or TA) to perform this "
                "lifecycle transition."
            ),
        )
        self.actor = actor


class GuardFailedError(IllegalTransitionError):
    """Raised when a transition guard precondition fails."""

    def __init__(self, guard: str, message: str = ""):
        super().__init__(
            "",
            "",
            "entity",
            message=(
                message
                or f"Guard condition {guard!r} failed. Verify that all prerequisite "
                "conditions and schedules are satisfied before retrying."
            ),
        )
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


# Declarative transition tables
MATERIAL_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        MaterialStatus.DRAFT,
        MaterialStatus.SCHEDULED,
        "lms.material.create",
        frozenset({"INSTRUCTOR"}),
        ("future_release_date",),
    ),
    Transition(
        MaterialStatus.DRAFT,
        MaterialStatus.PUBLISHED,
        "lms.material.publish",
        frozenset({"INSTRUCTOR"}),
        ("release_date_reached",),
    ),
    Transition(
        MaterialStatus.SCHEDULED,
        MaterialStatus.PUBLISHED,
        "lms.material.publish",
        frozenset({"INSTRUCTOR", "SYSTEM"}),
        ("release_date_reached",),
    ),
    Transition(
        MaterialStatus.PUBLISHED,
        MaterialStatus.ARCHIVED,
        "lms.material.delete",
        frozenset({"INSTRUCTOR"}),
    ),
)

ASSIGNMENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        AssignmentStatus.DRAFT,
        AssignmentStatus.SCHEDULED,
        "lms.assignment.create",
        frozenset({"INSTRUCTOR"}),
        ("future_release_date",),
    ),
    Transition(
        AssignmentStatus.DRAFT,
        AssignmentStatus.PUBLISHED,
        "lms.assignment.publish",
        frozenset({"INSTRUCTOR"}),
        ("release_date_reached",),
    ),
    Transition(
        AssignmentStatus.SCHEDULED,
        AssignmentStatus.PUBLISHED,
        "lms.assignment.publish",
        frozenset({"INSTRUCTOR", "SYSTEM"}),
        ("release_date_reached",),
    ),
    Transition(
        AssignmentStatus.PUBLISHED,
        AssignmentStatus.CLOSED,
        "lms.assignment.update",
        frozenset({"INSTRUCTOR", "SYSTEM"}),
    ),
    Transition(
        AssignmentStatus.SCHEDULED,
        AssignmentStatus.CLOSED,
        "lms.assignment.update",
        frozenset({"INSTRUCTOR", "SYSTEM"}),
    ),
    Transition(
        AssignmentStatus.CLOSED,
        AssignmentStatus.ARCHIVED,
        "lms.assignment.delete",
        frozenset({"INSTRUCTOR"}),
    ),
)

GRADE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        GradeStatus.DRAFT,
        GradeStatus.PUBLISHED,
        "lms.grade.publish",
        frozenset({"INSTRUCTOR"}),
    ),
    Transition(
        GradeStatus.PUBLISHED,
        GradeStatus.PUBLISHED,
        "lms.grade.update",
        frozenset({"INSTRUCTOR"}),
        ("requires_audit",),
    ),
)

_MATERIAL_INDEX = {(t.frm, t.to): t for t in MATERIAL_TRANSITIONS}
_ASSIGNMENT_INDEX = {(t.frm, t.to): t for t in ASSIGNMENT_TRANSITIONS}
_GRADE_INDEX = {(t.frm, t.to): t for t in GRADE_TRANSITIONS}


def resolve_material_transition(frm: str, to: str, actor: str | None = None) -> Transition:
    t = _MATERIAL_INDEX.get((frm, to))
    if not t:
        raise IllegalTransitionError(frm, to, "material")
    if actor and actor not in t.actors:
        raise ActorNotAllowedError(actor, frm, to, "material")
    return t


def resolve_assignment_transition(frm: str, to: str, actor: str | None = None) -> Transition:
    t = _ASSIGNMENT_INDEX.get((frm, to))
    if not t:
        raise IllegalTransitionError(frm, to, "assignment")
    if actor and actor not in t.actors:
        raise ActorNotAllowedError(actor, frm, to, "assignment")
    return t


def resolve_grade_transition(frm: str, to: str, actor: str | None = None) -> Transition:
    t = _GRADE_INDEX.get((frm, to))
    if not t:
        raise IllegalTransitionError(frm, to, "grade")
    if actor and actor not in t.actors:
        raise ActorNotAllowedError(actor, frm, to, "grade")
    return t


class MaterialFSM:
    @staticmethod
    def publish(release_date: datetime | None, now: datetime) -> str:
        target = (
            MaterialStatus.SCHEDULED
            if (release_date and release_date > now)
            else MaterialStatus.PUBLISHED
        )
        resolve_material_transition(MaterialStatus.DRAFT, target, "INSTRUCTOR")
        return target

    @staticmethod
    def auto_release(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != MaterialStatus.SCHEDULED:
            raise IllegalTransitionError(
                current_status,
                MaterialStatus.PUBLISHED,
                "material",
                f"Cannot auto-release material in {current_status} status. "
                "Ensure the material is in SCHEDULED status.",
            )
        if release_date and release_date > now:
            raise GuardFailedError(
                "release_date_reached",
                "Release time has not yet arrived. "
                "Wait until the scheduled release date or update the release timestamp.",
            )
        resolve_material_transition(current_status, MaterialStatus.PUBLISHED, "SYSTEM")
        return MaterialStatus.PUBLISHED


class AssignmentFSM:
    @staticmethod
    def publish(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != AssignmentStatus.DRAFT:
            raise IllegalTransitionError(
                current_status,
                AssignmentStatus.PUBLISHED,
                "assignment",
                f"Only DRAFT assignments may be published, got {current_status}. "
                "Create a new assignment or edit the draft before publishing.",
            )
        target = (
            AssignmentStatus.SCHEDULED
            if (release_date and release_date > now)
            else AssignmentStatus.PUBLISHED
        )
        resolve_assignment_transition(current_status, target, "INSTRUCTOR")
        return target

    @staticmethod
    def auto_release(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != AssignmentStatus.SCHEDULED:
            raise IllegalTransitionError(
                current_status,
                AssignmentStatus.PUBLISHED,
                "assignment",
                f"Only SCHEDULED assignments may be auto-released, got {current_status}. "
                "Schedule the assignment or publish it directly.",
            )
        if release_date and release_date > now:
            raise GuardFailedError(
                "release_date_reached",
                "Release time has not yet arrived. "
                "Wait until the scheduled release date or update the release timestamp.",
            )
        resolve_assignment_transition(current_status, AssignmentStatus.PUBLISHED, "SYSTEM")
        return AssignmentStatus.PUBLISHED

    @staticmethod
    def close(current_status: str) -> str:
        if current_status not in (AssignmentStatus.PUBLISHED, AssignmentStatus.SCHEDULED):
            raise IllegalTransitionError(
                current_status,
                AssignmentStatus.CLOSED,
                "assignment",
                f"Cannot close assignment in {current_status} status. "
                "Publish or schedule the assignment before closing it.",
            )
        resolve_assignment_transition(current_status, AssignmentStatus.CLOSED, "INSTRUCTOR")
        return AssignmentStatus.CLOSED


class GradeFSM:
    @staticmethod
    def publish(current_status: str) -> str:
        if current_status != GradeStatus.DRAFT:
            raise IllegalTransitionError(
                current_status,
                GradeStatus.PUBLISHED,
                "grade",
                f"Only DRAFT grades may be published, got {current_status}. "
                "Ensure grades are in draft status before publishing.",
            )
        resolve_grade_transition(current_status, GradeStatus.PUBLISHED, "INSTRUCTOR")
        return GradeStatus.PUBLISHED
