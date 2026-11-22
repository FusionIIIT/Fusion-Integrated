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
            "Your acting course role cannot perform this action.", "LMS_ROLE_DENIED"
        )


def nonempty(value, label):
    if not value.strip():
        raise RuleViolation(f"{label} must not be empty.")


def points(value):
    if not value.is_finite() or value < Decimal(0):
        raise RuleViolation("Points must be a finite nonnegative number.")


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
        parsed = urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username:
            raise RuleViolation("Use an HTTP or HTTPS link without embedded credentials.")


def assignment(instructions, due_at, submission_type, points_possible):
    nonempty(instructions, "Instructions")
    if due_at is None or due_at.utcoffset() is None:
        raise RuleViolation("An aware due date is required.")
    if submission_type not in ("FILE", "TEXT", "LINK"):
        raise RuleViolation("Choose FILE, TEXT or LINK.")
    points(points_possible)


def submission(assignment_kind, submitted_kind, now, due_at):
    if assignment_kind != submitted_kind:
        raise RuleViolation(
            "The submission type must match the assignment.", "SUBMISSION_TYPE_MISMATCH"
        )
    if now > due_at:
        raise RuleViolation("The assignment due date has passed.", "SUBMISSION_DUE_DATE_EXCEEDED")


def edit_assignment(old, new, *, has_submissions, has_grades, last_submission_at=None):
    if has_submissions:
        if old["submission_type"] != new["submission_type"]:
            raise RuleViolation("Submission type cannot change after a successful submission.")
        if new["due_at"] < old["due_at"] or (
            last_submission_at is not None and new["due_at"] < last_submission_at
        ):
            raise RuleViolation("The due date can only be extended after submissions exist.")
    if has_grades and old["points_possible"] != new["points_possible"]:
        raise RuleViolation("Points possible cannot change after grading has begun.")
