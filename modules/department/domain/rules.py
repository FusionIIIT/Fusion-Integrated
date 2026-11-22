"""Business rules as pure functions; every branch is tested without a database."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, time

from modules.department.domain.errors import RuleViolation
from modules.department.domain.roles import (
    DEPT_ADMIN,
    FACULTY,
    HOD,
    STUDENT,
)

# -- announcements (BR-DEPT-002, BR-DEPT-003) ------------------------------------
AUDIENCE_ROLES = ("student", "faculty", "dept_admin", "hod", "all")
TITLE_MAX = 200
BODY_MAX = 5000


def validate_announcement(
    *, title: str, body: str, audience_role: str, programme: str = "", batch_year: int | None = None
) -> None:
    """BR-DEPT-003: content and target scope must be present and valid."""
    problems = []
    if not (title or "").strip():
        problems.append({"field": "title", "message": "Give the announcement a title."})
    elif len(title) > TITLE_MAX:
        problems.append(
            {"field": "title", "message": f"Keep the title under {TITLE_MAX} characters."}
        )
    if not (body or "").strip():
        problems.append({"field": "body", "message": "Write the announcement's text."})
    elif len(body) > BODY_MAX:
        problems.append({"field": "body", "message": f"Keep the text under {BODY_MAX} characters."})
    if audience_role not in AUDIENCE_ROLES:
        problems.append(
            {
                "field": "audience_role",
                "message": "Choose who it is for: student, faculty, dept_admin, hod or all.",
            }
        )
    if batch_year is not None and not 2000 <= batch_year <= 2100:
        problems.append(
            {"field": "batch_year", "message": "Give a batch year such as 2024, or leave it empty."}
        )
    if len(programme or "") > 40:
        problems.append(
            {
                "field": "programme",
                "message": "Give a programme name such as B.Tech, or leave it empty.",
            }
        )
    if problems:
        raise RuleViolation(
            "announcement_incomplete",
            "The announcement cannot be published until these are fixed.",
            problems,
        )


# -- stock (BR-DEPT-015, AFR-DEPT-013) -------------------------------------------
def check_availability(*, requested: int, available: int) -> None:
    if requested <= 0:
        raise RuleViolation("invalid_quantity", "Ask for at least one unit.")
    if requested > available:
        raise RuleViolation(
            "insufficient_stock",
            f"Only {available} in stock, so a request for {requested} cannot go to the HOD. "
            "Ask for fewer or wait for a receipt.",
        )


def check_receipt(quantity: int) -> None:
    if quantity <= 0:
        raise RuleViolation("invalid_quantity", "A receipt must add at least one unit.")


# -- timetable (BR-DEPT-010, Q6) -------------------------------------------------
@dataclass(frozen=True)
class Slot:
    key: str
    day_of_week: int
    starts_at: time
    ends_at: time
    room: str
    programme: str
    batch_year: int | None


def validate_slot(slot: Slot) -> None:
    if not 0 <= slot.day_of_week <= 6:
        raise RuleViolation("invalid_slot", "Day of week must be 0 (Monday) to 6 (Sunday).")
    if slot.ends_at <= slot.starts_at:
        raise RuleViolation("invalid_slot", "A slot must end after it starts.")


def _clash(a: Slot, b: Slot) -> bool:
    if a.day_of_week != b.day_of_week:
        return False
    if not (a.starts_at < b.ends_at and b.starts_at < a.ends_at):
        return False
    same_room = bool(a.room) and a.room.strip().lower() == b.room.strip().lower()
    same_group = (
        bool(a.programme)
        and a.programme == b.programme
        and a.batch_year is not None
        and a.batch_year == b.batch_year
    )
    return same_room or same_group


def find_overlaps(candidates: Sequence[Slot], existing: Iterable[Slot]) -> list[tuple[str, str]]:
    """Every clashing pair, among the candidates and against what is saved."""
    pool = list(existing)
    return [
        (cand.key, other.key)
        for i, cand in enumerate(candidates)
        for other in [*candidates[:i], *pool]
        if other.key != cand.key and _clash(cand, other)
    ]


# -- official department details (BR-DEPT-011, AFR-DEPT-053) ---------------------
OFFICIAL_FIELDS = ("name", "core_policies")
NAME_MAX = 120  # the Department.name column
GENERAL_FIELDS = ("description", "contact_email", "contact_phone", "office_location", "website")


def validate_official_change(field: str, value: str) -> None:
    if field not in OFFICIAL_FIELDS:
        raise RuleViolation(
            "not_official_field",
            "Only the name and core policies go through HOD approval; "
            "headship follows the active HOD assignment.",
        )
    if field == "name" and not (value or "").strip():
        raise RuleViolation("invalid_value", "A department needs a name.")
    if field == "name" and len(value) > NAME_MAX:
        raise RuleViolation(
            "invalid_value", f"Keep the department name under {NAME_MAX} characters."
        )


def check_general_update(fields: Iterable[str]) -> None:
    official = sorted(set(fields) & set(OFFICIAL_FIELDS))
    if official:
        raise RuleViolation(
            "official_field",
            f"{', '.join(official)} is an official detail; propose it for HOD approval instead.",
        )


# -- feedback (AFR-DEPT-020, Q11) ------------------------------------------------
FEEDBACK_CATEGORIES = ("academic", "infrastructure", "administrative", "facilities", "other")


def check_category(category: str) -> None:
    if category and category not in FEEDBACK_CATEGORIES:
        raise RuleViolation(
            "invalid_category",
            f"Choose one of: {', '.join(FEEDBACK_CATEGORIES)}, or leave it empty.",
        )


# -- role tenure (BR-DEPT-021..024, Q1) ------------------------------------------
@dataclass(frozen=True)
class Tenure:
    key: int | None
    user_id: int
    valid_from: datetime
    valid_to: datetime


def validate_interval(valid_from: datetime, valid_to: datetime) -> None:
    if valid_to <= valid_from:
        raise RuleViolation("invalid_interval", "A tenure must end after it starts.")


def overlapping(candidate: Tenure, others: Iterable[Tenure]) -> list[Tenure]:
    """BR-DEPT-022: never two tenures of one role in effect at once."""
    return [
        o
        for o in others
        if o.key != candidate.key
        and candidate.valid_from < o.valid_to
        and o.valid_from < candidate.valid_to
    ]


def check_shortening(
    *, current: Tenure, new_valid_to: datetime, successors: Iterable[Tenure], now: datetime
) -> None:
    """Q1: ending a tenure early must not open a gap unless someone starts then."""
    if new_valid_to >= current.valid_to or new_valid_to <= now:
        return
    if not any(s.valid_from == new_valid_to for s in successors if s.key != current.key):
        raise RuleViolation(
            "would_leave_gap",
            "Record the successor first; ending this tenure early leaves the role with nobody.",
        )


# -- profiles (BR-DEPT-019, Q2, Q8) ----------------------------------------------
BASIC, LIMITED, FULL = "basic", "limited", "full"
PROFILE_KINDS = ("faculty", "student", "alumni")


def tier_for(viewer_role: str | None, target_kind: str) -> str | None:
    """None means the viewer may not see this profile at all."""
    if viewer_role in (HOD, DEPT_ADMIN):
        return FULL
    if viewer_role == FACULTY:
        return BASIC if target_kind == "student" else LIMITED
    if viewer_role == STUDENT:
        return BASIC if target_kind in ("student", "faculty") else None
    return None


TIER_FIELDS = {
    BASIC: ("id", "kind", "display_name", "programme", "department"),
    LIMITED: (
        "id",
        "kind",
        "display_name",
        "programme",
        "department",
        "email",
        "office",
        "research_interests",
        "current_position",
    ),
    FULL: (
        "id",
        "kind",
        "user_id",
        "username",
        "display_name",
        "programme",
        "department",
        "discipline",
        "batch_year",
        "email",
        "office",
        "research_interests",
        "bio",
        "graduation_year",
        "current_position",
        "is_active",
    ),
}

ASSIGNABLE_ROLES = (HOD, DEPT_ADMIN)
EMPLOYEE_KINDS = ("faculty", "staff")
