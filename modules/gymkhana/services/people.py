"""Who is a valid student or faculty member, asked of the directory (BR-GYM-001, BR-GYM-002)."""
from __future__ import annotations

from core.api.exceptions import BadRequestError, DomainError, PermissionDeniedError
from fusion_auth.client import IamUnavailable, get_client
from modules.directory import contracts as directory
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import IdentityUnavailableError

STUDENT = "student"
FACULTY = "faculty"
MIN_QUERY = 2
SEARCH_LIMIT = 25

_LABELS = {STUDENT: "a student", FACULTY: "a faculty member"}


def _require_kind(kind: str, assignments: dict[str, int]) -> dict[str, directory.UserDTO]:
    """Each field must name a person of this kind; every bad one is reported together."""
    people = directory.get_users(list(assignments.values()))
    bad, found = [], {}
    for field, user_id in assignments.items():
        person = people.get(user_id)
        if person is None or person.kind != kind:
            bad.append({"field": field,
                        "message": f"User {user_id} could not be confirmed as "
                                   f"{_LABELS[kind]} in the institute directory."})
        else:
            found[field] = person
    if bad:
        raise DomainError(
            f"Choose {_LABELS[kind]} for each highlighted field.",
            code=f"invalid_{kind}", details=bad)
    return found


def require_students(assignments: dict[str, int]) -> dict[str, directory.UserDTO]:
    return _require_kind(STUDENT, assignments)


def require_faculty(assignments: dict[str, int]) -> dict[str, directory.UserDTO]:
    return _require_kind(FACULTY, assignments)


def cohort_of(user_id: int) -> tuple[int | None, str]:
    """A student's batch year and branch, or (None, "") if the directory does not know them."""
    person = directory.get_users([user_id]).get(user_id)
    if person is None or person.kind != STUDENT:
        return None, ""
    return person.batch_year, person.discipline or ""


def search(*, actor, q: str, kind: str) -> list[dict]:
    """The people picker: for Student Admin and current Club Heads only."""
    require(actor, "gymkhana.club.create", "gymkhana.leadership.assign",
            "gymkhana.event_report.create")
    if not (scoping.is_student_admin(actor) or scoping.led_clubs(actor).exists()):
        raise PermissionDeniedError(
            "Only Student Admin and current club coordinators can search for people.",
            code="not_a_club_head")
    if kind not in _LABELS:
        raise BadRequestError("kind must be student or faculty.", code="invalid_filter")
    q = (q or "").strip()
    if len(q) < MIN_QUERY:
        return []
    try:
        rows = get_client().search_users(q=q, kind=kind, limit=SEARCH_LIMIT)
    except IamUnavailable as exc:
        raise IdentityUnavailableError() from exc
    return [{"user_id": r.user_id, "username": r.username,
             "display_name": r.display_name, "kind": r.kind}
            for r in rows if r.kind == kind and r.is_active]
