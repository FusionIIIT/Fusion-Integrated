"""Fast unit tests for pure Python domain logic in modules/complaints/domain/."""
from datetime import datetime, timezone
import pytest

from modules.complaints.domain import (
    ComplaintPriority,
    ComplaintStatus,
    InvalidTransition,
    MandatoryFieldMissing,
    AttachmentConstraintError,
    FeedbackNotAllowed,
    ReopeningNotAllowed,
    EscalationNotAllowed,
    RoleCardinalityError,
    RuleViolation,
    validate_attachment,
    validate_escalation_eligibility,
    validate_feedback_eligibility,
    validate_priority,
    validate_reopening_eligibility,
    validate_role_assignment,
    validate_submission_fields,
    validate_transition,
)


def test_mandatory_fields_validation():
    validate_submission_fields("Hostel", "Fan not working")

    with pytest.raises(MandatoryFieldMissing) as exc_info:
        validate_submission_fields("", "Description")
    assert exc_info.value.field_name == "category"

    with pytest.raises(MandatoryFieldMissing) as exc_info:
        validate_submission_fields("Hostel", "   ")
    assert exc_info.value.field_name == "description"


def test_priority_validation():
    assert validate_priority("low") == ComplaintPriority.LOW
    assert validate_priority("Medium") == ComplaintPriority.MEDIUM
    assert validate_priority("HIGH") == ComplaintPriority.HIGH

    with pytest.raises(RuleViolation) as exc_info:
        validate_priority("urgent")
    assert exc_info.value.code == "invalid_priority"


def test_attachment_validation():
    validate_attachment("photo.jpg", 1024)
    validate_attachment("report.pdf", 5 * 1024 * 1024)

    # Exceed size
    with pytest.raises(AttachmentConstraintError):
        validate_attachment("huge.pdf", 15 * 1024 * 1024)

    # Disallowed extension
    with pytest.raises(AttachmentConstraintError):
        validate_attachment("script.exe", 1024)


def test_legal_state_transitions():
    # Submitted -> In Progress
    t = validate_transition(ComplaintStatus.SUBMITTED, ComplaintStatus.IN_PROGRESS, permissions={"*"})
    assert t.frm == ComplaintStatus.SUBMITTED and t.to == ComplaintStatus.IN_PROGRESS

    # In Progress -> Resolved with resolution details
    t = validate_transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        permissions={"*"},
        resolution_details="Fixed fuse",
    )
    assert t.to == ComplaintStatus.RESOLVED

    # Resolved -> Closed
    t = validate_transition(ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, permissions={"*"})
    assert t.to == ComplaintStatus.CLOSED

    # Closed -> In Progress (reopen)
    t = validate_transition(ComplaintStatus.CLOSED, ComplaintStatus.IN_PROGRESS, permissions={"*"})
    assert t.to == ComplaintStatus.IN_PROGRESS


def test_illegal_state_transitions():
    # Cannot resolve without details
    with pytest.raises(RuleViolation) as exc_info:
        validate_transition(ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED, permissions={"*"}, resolution_details="")
    assert exc_info.value.code == "resolution_details_required"

    # Cannot reject without reason
    with pytest.raises(RuleViolation) as exc_info:
        validate_transition(ComplaintStatus.SUBMITTED, ComplaintStatus.REJECTED, permissions={"*"}, rejection_reason="")
    assert exc_info.value.code == "rejection_reason_required"

    # Cannot jump from Submitted to Closed directly
    with pytest.raises(InvalidTransition):
        validate_transition(ComplaintStatus.SUBMITTED, ComplaintStatus.CLOSED, permissions={"*"})

    # Cannot transition to same status
    with pytest.raises(InvalidTransition):
        validate_transition(ComplaintStatus.SUBMITTED, ComplaintStatus.SUBMITTED, permissions={"*"})


def test_permission_enforcement_in_transition():
    # Missing permission
    with pytest.raises(RuleViolation) as exc_info:
        validate_transition(
            ComplaintStatus.SUBMITTED,
            ComplaintStatus.IN_PROGRESS,
            permissions={"complaints.complaint.view"},
        )
    assert exc_info.value.code == "permission_denied"


def test_reopening_and_feedback_eligibility():
    # Only closed can reopen
    validate_reopening_eligibility(ComplaintStatus.CLOSED)
    with pytest.raises(ReopeningNotAllowed):
        validate_reopening_eligibility(ComplaintStatus.RESOLVED)

    # Feedback only for resolved or closed
    validate_feedback_eligibility(ComplaintStatus.RESOLVED, 5)
    validate_feedback_eligibility(ComplaintStatus.CLOSED, 1)
    with pytest.raises(FeedbackNotAllowed):
        validate_feedback_eligibility(ComplaintStatus.IN_PROGRESS, 4)

    with pytest.raises(RuleViolation) as exc_info:
        validate_feedback_eligibility(ComplaintStatus.RESOLVED, 6)
    assert exc_info.value.code == "invalid_rating"


def test_escalation_eligibility():
    validate_escalation_eligibility(ComplaintStatus.SUBMITTED, is_escalated=False)
    validate_escalation_eligibility(ComplaintStatus.IN_PROGRESS, is_escalated=False)

    with pytest.raises(EscalationNotAllowed):
        validate_escalation_eligibility(ComplaintStatus.RESOLVED, is_escalated=False)

    with pytest.raises(EscalationNotAllowed):
        validate_escalation_eligibility(ComplaintStatus.SUBMITTED, is_escalated=True)


def test_role_assignment_validation():
    now = datetime.now(timezone.utc)
    validate_role_assignment("complaint_handler", now, None)

    with pytest.raises(RoleCardinalityError):
        validate_role_assignment("unknown_role", now, None)

    with pytest.raises(RuleViolation) as exc_info:
        validate_role_assignment("complaint_supervisor", now, now)
    assert exc_info.value.code == "invalid_role_duration"

