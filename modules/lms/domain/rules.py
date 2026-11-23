"""Source rules and adopted policy decisions, independent of framework state."""

from decimal import Decimal
from urllib.parse import urlsplit


class RuleViolation(Exception):
    def __init__(self, message, code="LMS_RULE_VIOLATION"):
        super().__init__(message)
        self.code = code


def require_role(role, allowed):
    if role not in allowed:
        raise RuleViolation(
            "Switch to an authorized course role or ask the assigned instructor for help.",
            "LMS_ROLE_DENIED",
        )


def independent_grader(grader_user_id, owner_user_id):
    if grader_user_id == owner_user_id:
        raise RuleViolation(
            "Ask another authorized grader to handle your submission.",
            "CANNOT_GRADE_OWN_SUBMISSION",
        )


def nonempty(value, label):
    if not value.strip():
        raise RuleViolation(f"Enter a nonempty {label.lower()}.")


def points(value):
    if not value.is_finite() or value < Decimal(0):
        raise RuleViolation("Enter points as a finite nonnegative number.")


def payload(kind, text="", url="", has_file=False, *, material=False):
    text_kind = "NOTE" if material else "TEXT"
    valid = (
        (kind == text_kind and bool(text.strip()) and not url and not has_file)
        or (kind == "LINK" and bool(url) and not text and not has_file)
        or (kind == "FILE" and has_file and not text and not url)
    )
    if not valid:
        raise RuleViolation("Provide exactly the payload required by the content type.")
    if url:
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise RuleViolation("Use a valid HTTP or HTTPS link.") from exc
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username:
            raise RuleViolation("Use an HTTP or HTTPS link without embedded credentials.")


def assignment(instructions, due_at, submission_type, points_possible):
    nonempty(instructions, "Instructions")
    if due_at is None or due_at.utcoffset() is None:
        raise RuleViolation("Enter a due date with a timezone.")
    if submission_type not in ("FILE", "TEXT", "LINK"):
        raise RuleViolation("Choose FILE, TEXT or LINK.")
    points(points_possible)


def submission(assignment_kind, submitted_kind, now, due_at):
    if assignment_kind != submitted_kind:
        raise RuleViolation(
            "Choose the submission type required by the assignment.", "SUBMISSION_TYPE_MISMATCH"
        )
    if now > due_at:
        raise RuleViolation(
            "The due date has passed. Ask your instructor whether an extension is available.",
            "SUBMISSION_DUE_DATE_EXCEEDED",
        )


def edit_assignment(old, new, *, has_submissions, has_grades, last_submission_at=None):
    if has_submissions:
        if old["submission_type"] != new["submission_type"]:
            raise RuleViolation(
                "Keep the submission type; create a new assignment if a different type is needed."
            )
        if new["due_at"] < old["due_at"] or (
            last_submission_at is not None and new["due_at"] < last_submission_at
        ):
            raise RuleViolation("Keep or extend the due date because submissions already exist.")
    if has_grades and old["points_possible"] != new["points_possible"]:
        raise RuleViolation(
            "Keep the existing points possible; create a new assignment for a different total."
        )
