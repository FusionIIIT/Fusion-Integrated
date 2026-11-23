"""Workflow (WF) tests for initial review, revision, expiration, and rejection.

Covers:
- WF-TC-001 (BW-PMS-01: Step 1-3 (Initial Review Approval Path))
- WF-TC-002 (BW-PMS-01: Step 1 Guard (Submission Validation Failure))
- WF-TC-003 (BW-PMS-01: Step 3 Guard (Review Justification < 50 Characters))
- WF-TC-004 (BW-PMS-02: Step 1-4 (Revision and Re-Approval Path))
- WF-TC-005 (BW-PMS-02: Step 2 Guard (Resubmission After 60 Days / Unaddressed Feedback))
- WF-TC-021 (CW-PMS-01: Step 1-7 (Initial Review Reject Outcome))
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain.errors import (
    ExternalServiceUnavailableError,
    InsufficientJustificationError,
    InvalidDocumentError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.services import (
    assign_director,
    monitor_and_process_deadlines,
    revise_and_resubmit_application,
    submit_application,
    submit_director_review,
)

pytestmark = pytest.mark.django_db


def test_wf_tc_001_bw_pms_01_initial_review_approval_path():
    """WF-TC-001 | BW-PMS-01: Step 1-3 (Initial Review Approval Path).

    Verify a patent application transitions from Draft / Not Submitted through
    submission, Director assignment, and Director approval to Approved.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Adaptive Cooling System",
        abstract="Thermal control apparatus for high-density compute racks.",
        detailed_description="Full technical specification of microfluidic cooling channels.",
        claims="1. A thermal management system comprising...",
        domain="Mechanical Engineering",
    )
    assert app.status == PatentApplicationStatus.SUBMITTED.value

    assigned_app = assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    assert assigned_app.status == PatentApplicationStatus.UNDER_REVIEW.value
    assert assigned_app.assigned_director_user_id == 3001

    justification = (
        "The invention demonstrates clear technical novelty and non-obviousness "
        "over existing cooling assemblies."
    )
    review = submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification=justification,
        feedback="Approved for prosecution.",
    )
    assert review.decision == "Approve"
    assert review.justification == justification

    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_wf_tc_002_bw_pms_01_step_1_guard_submission_validation_failure():
    """WF-TC-002 | BW-PMS-01: Step 1 Guard (Submission Validation Failure).

    Verify application submission is rejected when completeness or document
    validation fails.
    """
    with pytest.raises(PreconditionNotMetError):
        submit_application(
            applicant_user_id=1001,
            title="",
            abstract="Abstract text",
            detailed_description="Detailed description text",
            claims="1. A claim.",
            domain="Computer Science",
        )

    with pytest.raises(InvalidDocumentError):
        submit_application(
            applicant_user_id=1001,
            title="Valid Title",
            abstract="Abstract text",
            detailed_description="Detailed description text",
            claims="1. A claim.",
            domain="Computer Science",
            documents_data=[
                {
                    "title": "Spec",
                    "filename": "spec.docx",
                    "file_size_bytes": 1024,
                }
            ],
        )

    with pytest.raises(InvalidDocumentError):
        submit_application(
            applicant_user_id=1001,
            title="Valid Title",
            abstract="Abstract text",
            detailed_description="Detailed description text",
            claims="1. A claim.",
            domain="Computer Science",
            documents_data=[
                {
                    "title": "Large Spec",
                    "filename": "spec.pdf",
                    "file_size_bytes": 60 * 1024 * 1024,
                }
            ],
        )

    with pytest.raises(ExternalServiceUnavailableError):
        submit_application(
            applicant_user_id=1001,
            title="Valid Title",
            abstract="Abstract text",
            detailed_description="Detailed description text",
            claims="1. A claim.",
            domain="Computer Science",
            documents_data=[
                {
                    "title": "Unscanned Spec",
                    "filename": "spec.pdf",
                    "file_size_bytes": 1024,
                    "is_clean": True,
                }
            ],
        )


def test_wf_tc_003_bw_pms_01_step_3_guard_review_justification_under_50_chars():
    """WF-TC-003 | BW-PMS-01: Step 3 Guard (Review Justification < 50 Characters).

    Verify Director review decision is not accepted when justification is fewer
    than 50 characters.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Optical Sensor Array",
        abstract="High-sensitivity optical sensing array.",
        detailed_description="Detailed optical architecture description.",
        claims="1. An optical sensor array...",
        domain="Physics",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )

    with pytest.raises(InsufficientJustificationError):
        submit_director_review(
            application_id=app.id,
            director_user_id=3001,
            decision="Approve",
            justification="Too brief justification.",
        )

    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.UNDER_REVIEW.value


def test_wf_tc_004_bw_pms_02_step_1_4_revision_and_reapproval_path():
    """WF-TC-004 | BW-PMS-02: Step 1-4 (Revision and Re-Approval Path).

    Verify an application sent to Needs Revision is revised and resubmitted within
    60 days, reassigned to a Director, and approved.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Distributed Consensus Protocol",
        abstract="Low-latency fault-tolerant consensus protocol.",
        detailed_description="Detailed state replication protocol description.",
        claims="1. A consensus protocol...",
        domain="Computer Science",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )

    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Needs Revision",
        justification=(
            "Independent claims require narrower scope regarding quorum "
            "recovery behavior under network partitions."
        ),
        feedback="Clarify quorum recovery steps in claims 1-3.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value

    revised_app = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response=(
            "Narrowed claims 1-3 to specify quorum recovery under partial "
            "network partitions."
        ),
        claims="1. A fault-tolerant consensus protocol with bounded quorum recovery...",
    )
    assert revised_app.status == PatentApplicationStatus.RESUBMITTED.value

    reassigned_app = assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    assert reassigned_app.status == PatentApplicationStatus.UNDER_REVIEW.value

    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification=(
            "The amended claims and partition recovery explanation satisfy "
            "technical review requirements."
        ),
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_wf_tc_005_bw_pms_02_step_2_guard_resubmission_after_60_days_or_unaddressed():
    """WF-TC-005 | BW-PMS-02: Step 2 Guard (Resubmission After 60 Days / Unaddressed Feedback).

    Verify resubmission is rejected or expires when outside the 60-day
    resubmission period or not addressing Director feedback.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Biopolymer Composite",
        abstract="Biodegradable structural polymer composite.",
        detailed_description="Detailed formulation and curing methodology.",
        claims="1. A biopolymer composite comprising...",
        domain="Materials Science",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Needs Revision",
        justification=(
            "Please provide tensile test ranges and address claim breadth in "
            "the independent claims."
        ),
        feedback="Provide tensile test ranges.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value

    # Unaddressed feedback is rejected
    with pytest.raises(PreconditionNotMetError):
        revise_and_resubmit_application(
            application_id=app.id,
            applicant_user_id=1001,
            feedback_response="",
            claims="1. Unchanged claim...",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value

    # Past 60-day resubmission deadline expires application
    app.revision_deadline = timezone.now() - timedelta(days=1)
    app.save(update_fields=["revision_deadline", "updated_at"])

    monitor_and_process_deadlines(now=timezone.now())
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.EXPIRED.value


def test_wf_tc_021_cw_pms_01_step_1_7_initial_review_reject_outcome():
    """WF-TC-021 | CW-PMS-01: Step 1-7 (Initial Review Reject Outcome).

    Verify an application in Under Review can be directly rejected by the
    Director.
    """
    app = submit_application(
        applicant_user_id=1001,
        title="Perpetual Motion Generator",
        abstract="Closed-loop self-sustaining energy generator.",
        detailed_description="Detailed apparatus layout.",
        claims="1. A self-sustaining generator...",
        domain="Physics",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )

    justification = (
        "The claimed apparatus does not demonstrate patentable technical "
        "utility or novelty over established prior art."
    )
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Reject",
        justification=justification,
        feedback="Application rejected during initial review.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REJECTED.value
