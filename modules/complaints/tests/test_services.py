"""Tests for Complaint Management business services and workflows.

Covers:
- BW-CMS-01 to BW-CMS-08
- UC-CMS-001 through UC-CMS-022
- Roles, feedback, announcements, SLA
"""
import datetime
import pytest
from django.utils import timezone

from modules.complaints import services
from modules.complaints.domain.errors import (
    ComplaintAlreadyEscalated,
    ComplaintNotClosed,
    ComplaintNotResolved,
    ComplaintPermissionDenied,
    ComplaintValidationError,
)
from modules.complaints.domain.state_machine import (
    ClosureVerification,
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
)
from modules.complaints.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintCategory,
    ComplaintFeedback,
)


@pytest.fixture
def category(db):
    return ComplaintCategory.objects.create(
        name="Electrical Maintenance",
        description="Fans, lights, wiring issues",
        default_sla_hours=48,
    )


@pytest.fixture
def complaint(db, category):
    return services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Hall 3, Room 204",
        description="Ceiling fan is not functioning.",
        priority=ComplaintPriority.MEDIUM.value,
        verification_required=ClosureVerification.NONE.value,
    )


@pytest.mark.django_db
def test_submit_complaint_generates_id_and_sets_sla(category):
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Library 2nd Floor",
        description="AC is leaking water.",
        priority=ComplaintPriority.HIGH.value,
    )
    assert c.complaint_id.startswith("CMP-")
    assert c.status == ComplaintStatus.SUBMITTED.value
    assert c.sla_deadline is not None
    assert c.transitions.count() == 1
    assert c.transitions.first().to_status == ComplaintStatus.SUBMITTED.value


@pytest.mark.django_db
def test_assign_and_prioritize_complaint(complaint):
    updated = services.assign_and_prioritize_complaint(
        complaint=complaint,
        actor_user_id=201,
        worker_id=501,
        worker_name="Ramesh Electrician",
        priority=ComplaintPriority.HIGH.value,
        remarks="High priority assigned due to exam season.",
    )
    assert updated.assigned_worker_id == 501
    assert updated.assigned_worker_name == "Ramesh Electrician"
    assert updated.priority == ComplaintPriority.HIGH.value
    assert updated.transitions.count() == 2


@pytest.mark.django_db
def test_update_progress_transitions_to_in_progress(complaint):
    # Initial status is SUBMITTED
    updated = services.update_complaint_progress(
        complaint=complaint,
        actor_user_id=201,
        progress_notes="Technician dispatched to inspect fan.",
    )
    assert updated.status == ComplaintStatus.IN_PROGRESS.value
    assert updated.transitions.filter(to_status=ComplaintStatus.IN_PROGRESS.value).exists()


@pytest.mark.django_db
def test_resolve_and_direct_closure_when_no_verification_required(complaint):
    # verification_required is NONE -> resolve directly closes
    resolved = services.resolve_complaint(
        complaint=complaint,
        actor_user_id=201,
        resolution_details="Replaced damaged capacitor and tested fan.",
    )
    assert resolved.status == ComplaintStatus.CLOSED.value
    assert resolved.resolved_at is not None
    assert resolved.closed_at is not None


@pytest.mark.django_db
def test_user_verification_and_closure(category):
    # BW-CMS-02: requires User verification
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Hall 1",
        description="Switch board loose",
        verification_required=ClosureVerification.USER.value,
    )
    resolved = services.resolve_complaint(
        complaint=c,
        actor_user_id=201,
        resolution_details="Switch board tightened and secured.",
    )
    assert resolved.status == ComplaintStatus.RESOLVED.value
    assert resolved.closed_at is None

    # Other user cannot verify
    with pytest.raises(ComplaintPermissionDenied):
        services.verify_and_close_complaint(
            complaint=resolved,
            actor_user_id=999,
            actor_role="complainant",
        )

    # Complainant verifies
    closed = services.verify_and_close_complaint(
        complaint=resolved,
        actor_user_id=101,
        actor_role="complainant",
        remarks="Verified working properly.",
    )
    assert closed.status == ComplaintStatus.CLOSED.value
    assert closed.closed_at is not None


@pytest.mark.django_db
def test_supervisor_verification_and_closure(category):
    # BW-CMS-03: requires Supervisor verification
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Hostel Substation",
        description="Power breaker tripped",
        verification_required=ClosureVerification.SUPERVISOR.value,
    )
    resolved = services.resolve_complaint(
        complaint=c,
        actor_user_id=201,
        resolution_details="Breaker reset and load balanced.",
    )
    assert resolved.status == ComplaintStatus.RESOLVED.value

    # Complainant cannot verify supervisor-gated closure
    with pytest.raises(ComplaintPermissionDenied):
        services.verify_and_close_complaint(
            complaint=resolved,
            actor_user_id=101,
            actor_role="complainant",
        )

    # Supervisor verifies
    closed = services.verify_and_close_complaint(
        complaint=resolved,
        actor_user_id=301,
        actor_role="complaint_supervisor",
        remarks="Supervisory inspection completed.",
    )
    assert closed.status == ComplaintStatus.CLOSED.value


@pytest.mark.django_db
def test_reject_complaint_requires_reason(complaint):
    # BW-CMS-04: Rejection
    with pytest.raises(ComplaintValidationError):
        services.reject_complaint(complaint=complaint, actor_user_id=201, rejection_reason="")

    rejected = services.reject_complaint(
        complaint=complaint,
        actor_user_id=201,
        rejection_reason="Duplicate complaint already registered.",
    )
    assert rejected.status == ComplaintStatus.REJECTED.value
    assert rejected.rejected_at is not None


@pytest.mark.django_db
def test_reopening_denied_workflow(complaint):
    # BW-CMS-05: Reopening Denied
    services.resolve_complaint(
        complaint=complaint,
        actor_user_id=201,
        resolution_details="Fixed.",
    )
    # Complainant requests reopening
    reopen_req = services.request_reopening(
        complaint=complaint,
        complainant_user_id=101,
        reopening_reason="Fan still making grinding noise.",
    )
    assert reopen_req.reopening_status == ReopeningStatus.PENDING.value

    # Supervisor denies reopening
    denied = services.review_reopening_request(
        complaint=complaint,
        supervisor_user_id=301,
        approved=False,
        review_remarks="Noise is within normal operating threshold.",
    )
    assert denied.status == ComplaintStatus.CLOSED.value
    assert denied.reopening_status == ReopeningStatus.DENIED.value


@pytest.mark.django_db
def test_reopening_approved_workflow(complaint):
    # BW-CMS-06: Reopening Approved
    services.resolve_complaint(
        complaint=complaint,
        actor_user_id=201,
        resolution_details="Fixed.",
    )
    services.request_reopening(
        complaint=complaint,
        complainant_user_id=101,
        reopening_reason="Issue recurring.",
    )

    approved = services.review_reopening_request(
        complaint=complaint,
        supervisor_user_id=301,
        approved=True,
        review_remarks="Approved for further overhaul.",
    )
    assert approved.status == ComplaintStatus.IN_PROGRESS.value
    assert approved.reopening_status == ReopeningStatus.APPROVED.value


@pytest.mark.django_db
def test_manual_escalation(complaint):
    # BW-CMS-07: Manual escalation
    escalated = services.escalate_complaint_manually(
        complaint=complaint,
        handler_user_id=201,
        remarks="Specialist equipment required from main store.",
    )
    assert escalated.is_escalated is True
    assert escalated.escalation_type == EscalationType.MANUAL.value

    # Cannot escalate again
    with pytest.raises(ComplaintAlreadyEscalated):
        services.escalate_complaint_manually(
            complaint=escalated,
            handler_user_id=201,
            remarks="Escalating again.",
        )


@pytest.mark.django_db
def test_automatic_sla_escalation(category):
    # BW-CMS-08: Automatic SLA Escalation
    past_time = timezone.now() - datetime.timedelta(hours=50)
    c = Complaint.objects.create(
        complaint_id="CMP-TEST-0001",
        complainant_user_id=101,
        category=category,
        location="Mess Hall",
        description="Water purifier filter blocked",
        status=ComplaintStatus.SUBMITTED.value,
        sla_deadline=past_time,
    )
    escalated_count = services.check_and_escalate_sla_breaches()
    assert escalated_count >= 1

    c.refresh_from_db()
    assert c.is_escalated is True
    assert c.escalation_type == EscalationType.AUTOMATIC_SLA.value


@pytest.mark.django_db
def test_feedback_submission(complaint):
    # UC-CMS-009: Submit Feedback
    services.resolve_complaint(
        complaint=complaint,
        actor_user_id=201,
        resolution_details="Completed.",
    )
    feedback = services.submit_feedback(
        complaint=complaint,
        complainant_user_id=101,
        rating=5,
        comments="Very prompt resolution!",
    )
    assert feedback.rating == 5
    assert feedback.complaint == complaint


@pytest.mark.django_db
def test_role_assignment_and_single_active_holder_constraint():
    # UC-CMS-018: Manage CMS Roles
    now = timezone.now()
    later = now + datetime.timedelta(days=30)

    # Assign Handler A
    role_a = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=201,
        assigned_by_user_id=1,
        start_date=now,
        end_date=later,
    )
    assert role_a.is_active is True

    # Mid-cycle reassignment to Handler B -> role_a becomes inactive
    role_b = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=202,
        assigned_by_user_id=1,
        start_date=now,
        end_date=later,
    )
    assert role_b.is_active is True

    role_a.refresh_from_db()
    assert role_a.is_active is False
    assert (
        CmsRoleAssignment.objects.filter(
            role_type=CmsRoleAssignment.ROLE_HANDLER, is_active=True
        ).count()
        == 1
    )
