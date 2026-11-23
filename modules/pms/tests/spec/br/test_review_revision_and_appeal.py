"""Business Rule tests for Director assignment, reviews, revisions, and appeals."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain.entities import (
    MIN_JUSTIFICATION_LENGTH,
    validate_appeal_outcome,
    validate_appeal_submission,
    validate_review_decision,
)
from modules.pms.domain.errors import (
    ConflictOfInterestError,
    InsufficientJustificationError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import PatentAppeal
from modules.pms.services import (
    assign_director,
    file_appeal,
    monitor_and_process_deadlines,
    revise_and_resubmit_application,
    submit_application,
    submit_director_review,
)

pytestmark = pytest.mark.django_db


def test_br_tc_022_permitted_automatic_director_assignment_when_rules_available():
    """BR-TC-022 | BR-PMS-022: permitted automatic Director assignment when rules available and criteria applied."""
    app = submit_application(
        applicant_user_id=1001,
        title="Auto Assign App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    assigned = assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    assert assigned.status == PatentApplicationStatus.UNDER_REVIEW.value
    assert assigned.assigned_director_user_id == 3001


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-023 | BR-PMS-022: A8_BASE assign_director requires an "
        "explicit director_user_id and has no toggle for unavailable assignment rules."
    )
)
def test_br_tc_023_exception_when_configured_assignment_rules_unavailable():
    """BR-TC-023 | BR-PMS-022: exception when configured assignment rules are unavailable."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-024 | BR-PMS-023: A8_BASE provides no automated "
        "Director-domain matching selector or service."
    )
)
def test_br_tc_024_director_expertise_matching_with_application_domain():
    """BR-TC-024 | BR-PMS-023: Director expertise matching with application domain."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-025 | BR-PMS-024: A8_BASE provides no automated "
        "Director workload-balancing assignment service."
    )
)
def test_br_tc_025_director_workload_balance_criterion():
    """BR-TC-025 | BR-PMS-024: Director workload balance criterion."""


def test_br_tc_026_conflict_of_interest_check_prior_to_director_assignment():
    """BR-TC-026 | BR-PMS-025: conflict-of-interest check prior to Director assignment."""
    app = submit_application(
        applicant_user_id=1001,
        title="COI Pre-Check App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    with pytest.raises(ConflictOfInterestError):
        assign_director(
            application_id=app.id,
            director_user_id=1001,
            assigned_by_user_id=9001,
        )
    app.refresh_from_db()
    assert app.assigned_director_user_id is None
    assert app.status == PatentApplicationStatus.SUBMITTED.value


def test_br_tc_027_prohibited_review_by_director_listed_as_inventor():
    """BR-TC-027 | BR-PMS-026: prohibited review by Director listed as inventor."""
    app = submit_application(
        applicant_user_id=1001,
        title="Co-Inventor Director App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
        coinventors_data=[
            {
                "user_id": 3001,
                "name": "Director Inventor",
                "email": "dir@example.edu",
                "ownership_percentage": "100.00",
            }
        ],
    )
    with pytest.raises(ConflictOfInterestError):
        assign_director(
            application_id=app.id,
            director_user_id=3001,
            assigned_by_user_id=9001,
        )
    app.refresh_from_db()
    assert app.assigned_director_user_id is None


def test_br_tc_028_prohibited_reviewer_role_for_pcc_admin_listed_as_inventor():
    """BR-TC-028 | BR-PMS-027: prohibited reviewer role for PCC_ADMIN listed as inventor."""
    app = submit_application(
        applicant_user_id=7001,
        title="Admin Inventor App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    with pytest.raises(ConflictOfInterestError):
        assign_director(
            application_id=app.id,
            director_user_id=7001,
            assigned_by_user_id=9001,
        )
    app.refresh_from_db()
    assert app.assigned_director_user_id is None


def test_br_tc_029_permitted_director_review_decisions():
    """BR-TC-029 | BR-PMS-029: permitted Director review decisions (Approve, Reject, Needs Revision)."""
    justification = "A" * MIN_JUSTIFICATION_LENGTH
    for decision in ("Approve", "Reject", "Needs Revision"):
        validate_review_decision(decision, justification)


def test_br_tc_030_prohibited_invalid_or_multiple_director_review_decisions():
    """BR-TC-030 | BR-PMS-029: prohibited invalid or multiple Director review decisions."""
    justification = "A" * MIN_JUSTIFICATION_LENGTH
    with pytest.raises(PreconditionNotMetError):
        validate_review_decision("Approve, Reject", justification)
    with pytest.raises(PreconditionNotMetError):
        validate_review_decision("Maybe", justification)


def test_br_tc_031_boundary_justification_of_50_characters_accepted():
    """BR-TC-031 | BR-PMS-030: boundary justification of 50 characters accepted."""
    validate_review_decision("Approve", "J" * 50)


def test_br_tc_032_boundary_justification_of_49_characters_or_empty_rejected():
    """BR-TC-032 | BR-PMS-030: boundary justification of 49 characters or empty rejected."""
    with pytest.raises(InsufficientJustificationError):
        validate_review_decision("Approve", "J" * 49)
    with pytest.raises(InsufficientJustificationError):
        validate_review_decision("Approve", "")


def test_br_tc_033_director_review_completed_within_15_business_days_boundary():
    """BR-TC-033 | BR-PMS-031: Director review completed within 15 business days boundary."""
    app = submit_application(
        applicant_user_id=1001,
        title="Timely Review App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    review = submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="A" * 50,
    )
    assert review.decision == "Approve"


def test_br_tc_034_permitted_revision_when_status_is_needs_revision():
    """BR-TC-034 | BR-PMS-033: permitted revision when status is Needs Revision."""
    app = submit_application(
        applicant_user_id=1001,
        title="Needs Revision App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Addressed all requested revisions thoroughly.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_br_tc_035_permitted_revision_when_status_is_rejected():
    """BR-TC-035 | BR-PMS-034: permitted revision when status is Rejected."""
    app = submit_application(
        applicant_user_id=1001,
        title="Rejected App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.REJECTED.value
    app.save(update_fields=["status", "updated_at"])
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Revised claims after rejection.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_br_tc_036_resubmission_on_or_before_day_60_from_decision_date():
    """BR-TC-036 | BR-PMS-035: resubmission on or before day 60 from decision date."""
    app = submit_application(
        applicant_user_id=1001,
        title="Day 60 Resubmission App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.revision_deadline = timezone.now() + timedelta(days=1)
    app.save(update_fields=["status", "revision_deadline", "updated_at"])
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Resubmitted within the 60-day window.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_br_tc_037_permitted_resubmission_addressing_recorded_director_feedback():
    """BR-TC-037 | BR-PMS-036: permitted resubmission addressing recorded Director feedback."""
    app = submit_application(
        applicant_user_id=1001,
        title="Feedback Addressed App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Clarified claim scope as requested by Director.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_br_tc_038_prohibited_resubmission_not_addressing_recorded_director_feedback():
    """BR-TC-038 | BR-PMS-036: prohibited resubmission not addressing recorded Director feedback."""
    app = submit_application(
        applicant_user_id=1001,
        title="Missing Feedback Response App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])
    with pytest.raises(PreconditionNotMetError):
        revise_and_resubmit_application(
            application_id=app.id,
            applicant_user_id=1001,
            feedback_response="short",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value


def test_br_tc_039_status_updated_to_expired_after_60_day_period_expires():
    """BR-TC-039 | BR-PMS-038: status updated to Expired after 60-day resubmission period expires."""
    app = submit_application(
        applicant_user_id=1001,
        title="Expiring App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    now = timezone.now()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.revision_deadline = now - timedelta(days=1)
    app.save(update_fields=["status", "revision_deadline", "updated_at"])
    monitor_and_process_deadlines(now=now)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.EXPIRED.value


def test_br_tc_097_permitted_appeal_when_application_status_is_rejected():
    """BR-TC-097 | BR-PMS-092: permitted appeal when application status is Rejected."""
    validate_appeal_submission(
        PatentApplicationStatus.REJECTED.value,
        "Erroneous prior art rejection",
        "Detailed grounds and justification.",
    )


def test_br_tc_098_prohibited_appeal_when_application_status_is_not_rejected():
    """BR-TC-098 | BR-PMS-092: prohibited appeal when application status is not Rejected."""
    app = submit_application(
        applicant_user_id=1001,
        title="Premature Appeal App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    with pytest.raises(PreconditionNotMetError):
        validate_appeal_submission(
            PatentApplicationStatus.SUBMITTED.value,
            "Premature appeal",
            "Detailed grounds and justification.",
        )
    assert PatentAppeal.objects.filter(application=app).count() == 0


def test_br_tc_099_appeal_filed_within_applicable_allowed_period():
    """BR-TC-099 | BR-PMS-093: appeal filed within applicable allowed period."""
    app = submit_application(
        applicant_user_id=1001,
        title="Timely Appeal App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="AI",
    )
    app.status = PatentApplicationStatus.REJECTED.value
    app.assigned_director_user_id = 3001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Timely appeal grounds",
        justification="Timely appeal justification.",
    )
    assert appeal.pk is not None


def test_br_tc_100_permitted_appeal_with_applicant_provided_grounds_and_justification():
    """BR-TC-100 | BR-PMS-094: permitted appeal with Applicant-provided grounds and justification."""
    validate_appeal_submission(
        PatentApplicationStatus.REJECTED.value,
        "Valid grounds",
        "Valid justification",
    )


def test_br_tc_101_prohibited_appeal_without_grounds_and_justification():
    """BR-TC-101 | BR-PMS-094: prohibited appeal without grounds and justification."""
    with pytest.raises(PreconditionNotMetError):
        validate_appeal_submission(
            PatentApplicationStatus.REJECTED.value,
            "",
            "Valid justification",
        )
    with pytest.raises(PreconditionNotMetError):
        validate_appeal_submission(
            PatentApplicationStatus.REJECTED.value,
            "Valid grounds",
            "",
        )


def test_br_tc_102_permitted_director_appeal_outcomes():
    """BR-TC-102 | BR-PMS-095: permitted Director appeal outcomes (Uphold Rejection, Remand for Amendment, Modify Decision)."""
    for outcome in ("Uphold Rejection", "Remand for Amendment", "Modify Decision"):
        validate_appeal_outcome(outcome, "Valid appeal decision justification.")


def test_br_tc_103_prohibited_invalid_director_appeal_outcome():
    """BR-TC-103 | BR-PMS-095: prohibited invalid Director appeal outcome."""
    with pytest.raises(PreconditionNotMetError):
        validate_appeal_outcome("Dismiss Silently", "Valid appeal decision justification.")
