"""PMS Review and Appeal Services.

Enforces business rules BR-PMS-022 to 031, BR-PMS-035, and BR-PMS-092 to 095.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import (
    check_director_conflict,
    validate_appeal_outcome,
    validate_appeal_submission,
    validate_review_decision,
)
from modules.pms.domain.errors import (
    ConflictOfInterestError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import (
    DirectorReview,
    PatentAppeal,
    PatentApplication,
)
from modules.pms.services.audit import log_audit
from modules.pms.services.deadlines import (
    calculate_review_deadline,
    calculate_revision_deadline,
)
from modules.pms.services.notifications import enqueue_notification


def assign_director(
    *,
    application_id: int,
    director_user_id: int,
    assigned_by_user_id: int,
) -> PatentApplication:
    """Assign an application to a Director for technical review (UC-PMS-007, CFR-PMS-006)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Status must be Submitted or Resubmitted
        if app.status not in (
            PatentApplicationStatus.SUBMITTED.value,
            PatentApplicationStatus.RESUBMITTED.value,
        ):
            raise PreconditionNotMetError(
                f"Application status '{app.status}' is not eligible for Director assignment."
            )

        # Conflict of interest check (BR-PMS-025, 026, 027)
        coinventor_ids = list(app.coinventors.values_list("user_id", flat=True))
        check_director_conflict(
            director_user_id=director_user_id,
            applicant_user_id=app.applicant_user_id,
            coinventor_user_ids=coinventor_ids,
        )
        if assigned_by_user_id == app.applicant_user_id or assigned_by_user_id in coinventor_ids:
            raise ConflictOfInterestError("PCC_ADMIN cannot assign an application they authored.")

        validate_transition(
            app.status, PatentApplicationStatus.UNDER_REVIEW, actor_role="PCC_ADMIN"
        )
        prev_status = app.status

        now = timezone.now()
        app.assigned_director_user_id = director_user_id
        app.director_assigned_at = now
        app.review_deadline = calculate_review_deadline(now)  # 15 business days (BR-PMS-031)
        app.status = PatentApplicationStatus.UNDER_REVIEW.value
        app.save()

        log_audit(
            application=app,
            actor_user_id=assigned_by_user_id,
            action_type="director_assigned",
            from_state=prev_status,
            to_state=app.status,
            details={
                "assigned_director_user_id": director_user_id,
                "review_deadline": str(app.review_deadline),
            },
        )

        enqueue_notification(
            topic="application.assigned_director",
            dedupe_key=f"pms:app:assigned_dir:{app.id}:{now.timestamp()}",
            subject=f"PMS: New Application Assigned for Review ({app.application_no})",
            body=f"You have been assigned to review patent application '{app.title}'. Deadline: {app.review_deadline}.",
            recipient_user_id=director_user_id,
        )

    return app


def submit_director_review(
    *,
    application_id: int,
    director_user_id: int,
    decision: str,
    justification: str,
    feedback: str = "",
) -> DirectorReview:
    """Submit a Director review decision with justification (UC-PMS-008, CFR-PMS-007)."""
    validate_review_decision(decision, justification)

    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Precondition check: application must be Under Review
        if app.status != PatentApplicationStatus.UNDER_REVIEW.value:
            raise PreconditionNotMetError(
                f"Application status '{app.status}' cannot be reviewed. Must be 'under_review'."
            )

        # Verify assigned reviewer
        if app.assigned_director_user_id != director_user_id:
            raise PreconditionNotMetError(
                f"User {director_user_id} is not the assigned Director for this application."
            )

        # Conflict check
        coinventor_ids = list(app.coinventors.values_list("user_id", flat=True))
        check_director_conflict(director_user_id, app.applicant_user_id, coinventor_ids)

        now = timezone.now()
        target_status_map = {
            "Approve": PatentApplicationStatus.APPROVED,
            "Reject": PatentApplicationStatus.REJECTED,
            "Needs Revision": PatentApplicationStatus.NEEDS_REVISION,
        }
        target_status = target_status_map[decision]

        validate_transition(app.status, target_status, actor_role="Director")
        prev_status = app.status

        app.status = target_status.value
        if target_status in (
            PatentApplicationStatus.NEEDS_REVISION,
            PatentApplicationStatus.REJECTED,
        ):
            app.revision_deadline = calculate_revision_deadline(
                now
            )  # 60 calendar days (BR-PMS-035)

        app.save()

        review = DirectorReview.objects.create(
            application=app,
            director_user_id=director_user_id,
            decision=decision,
            justification=justification.strip(),
            feedback=feedback.strip(),
        )

        log_audit(
            application=app,
            actor_user_id=director_user_id,
            action_type="director_reviewed",
            from_state=prev_status,
            to_state=app.status,
            details={
                "decision": decision,
                "justification": justification,
                "feedback": feedback,
            },
        )

        enqueue_notification(
            topic="application.reviewed",
            dedupe_key=f"pms:app:reviewed:{app.id}:{now.timestamp()}",
            subject=f"PMS: Review Decision - {decision} ({app.application_no})",
            body=f"Your application '{app.title}' received review decision: {decision}. Feedback: {feedback or justification}",
            recipient_user_id=app.applicant_user_id,
        )

    return review


def file_appeal(
    *,
    application_id: int,
    applicant_user_id: int,
    grounds: str,
    justification: str,
) -> PatentAppeal:
    """Submit an appeal against application rejection (UC-PMS-022, CFR-PMS-020)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        if app.applicant_user_id != applicant_user_id:
            raise PreconditionNotMetError("Only the primary applicant may file an appeal.")

        validate_appeal_submission(app.status, grounds, justification)
        validate_transition(
            app.status, PatentApplicationStatus.APPEAL_SUBMITTED, actor_role="Applicant"
        )
        prev_status = app.status

        app.status = PatentApplicationStatus.APPEAL_SUBMITTED.value
        app.save(update_fields=["status", "updated_at"])

        appeal = PatentAppeal.objects.create(
            application=app,
            applicant_user_id=applicant_user_id,
            grounds=grounds.strip(),
            justification=justification.strip(),
            status="submitted",
        )

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="appeal_submitted",
            from_state=prev_status,
            to_state=app.status,
            details={"appeal_id": appeal.id, "grounds": grounds},
        )

        enqueue_notification(
            topic="application.appeal_submitted",
            dedupe_key=f"pms:app:appeal_sub:{app.id}",
            subject=f"PMS: Appeal Submitted for {app.application_no}",
            body=f"An appeal has been submitted for rejected application '{app.title}'.",
            recipient_user_id=app.assigned_director_user_id or app.applicant_user_id,
        )

    return appeal


def review_appeal(
    *,
    appeal_id: int,
    director_user_id: int,
    outcome: str,
    outcome_justification: str,
) -> PatentAppeal:
    """Review and decide an appeal (UC-PMS-023, CFR-PMS-020)."""
    validate_appeal_outcome(outcome, outcome_justification)

    with transaction.atomic():
        appeal = PatentAppeal.objects.select_for_update().get(pk=appeal_id)
        app = appeal.application

        target_status_map = {
            "Remand for Amendment": PatentApplicationStatus.REMANDED_FOR_AMENDMENT,
            "Uphold Rejection": PatentApplicationStatus.REJECTION_UPHELD,
            "Modify Decision": PatentApplicationStatus.DECISION_MODIFIED,
        }
        target_status = target_status_map[outcome]

        validate_transition(app.status, target_status, actor_role="Director")
        prev_status = app.status

        appeal.outcome = outcome
        appeal.outcome_justification = outcome_justification.strip()
        appeal.director_user_id = director_user_id
        appeal.decided_at = timezone.now()
        appeal.status = outcome.lower().replace(" ", "_")
        appeal.save()

        # If decision modified, transition to Approved
        if target_status == PatentApplicationStatus.DECISION_MODIFIED:
            app.status = PatentApplicationStatus.APPROVED.value
        else:
            app.status = target_status.value
        app.save()

        log_audit(
            application=app,
            actor_user_id=director_user_id,
            action_type="appeal_reviewed",
            from_state=prev_status,
            to_state=app.status,
            details={"outcome": outcome, "justification": outcome_justification},
        )

        enqueue_notification(
            topic="application.appeal_reviewed",
            dedupe_key=f"pms:app:appeal_rev:{appeal.id}",
            subject=f"PMS: Appeal Outcome - {outcome} ({app.application_no})",
            body=f"Appeal on application '{app.title}' has been reviewed: {outcome}.",
            recipient_user_id=app.applicant_user_id,
        )

    return appeal
