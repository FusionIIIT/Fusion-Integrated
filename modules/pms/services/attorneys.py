"""PMS Attorney Assignment, Patentability, and Advice service.

Enforces business rules BR-PMS-040 through 046, and BR-PMS-127.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import validate_patentability_opinion
from modules.pms.domain.errors import (
    ConflictOfInterestError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
)
from modules.pms.models import (
    AttorneyAssignment,
    AttorneyPanel,
    PatentabilityAssessment,
    PatentApplication,
    PatentLegalAdvice,
)
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def assign_attorney(
    *,
    application_id: int,
    attorney_user_id: int,
    assigned_by_user_id: int,
    institutional_exception: bool = False,
) -> AttorneyAssignment:
    """Assign an attorney to an approved application (UC-PMS-010, CFR-PMS-009)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Assignment is an independent subworkflow; the application remains
        # Approved while the AttorneyAssignment row tracks offer/response.
        if app.status != PatentApplicationStatus.APPROVED.value:
            raise PreconditionNotMetError(
                f"Application status '{app.status}' cannot receive attorney assignment. "
                "Must be Approved (BR-PMS-040, BR-PMS-127)."
            )

        # Approved panel verification (BR-PMS-041)
        panel_entry = AttorneyPanel.objects.filter(
            attorney_user_id=attorney_user_id, is_approved=True
        ).first()
        if not panel_entry and not institutional_exception:
            raise PreconditionNotMetError(
                f"Attorney {attorney_user_id} is not on the approved attorney panel (BR-PMS-041)."
            )

        # Workload check (BR-PMS-043)
        if panel_entry and panel_entry.current_workload >= panel_entry.max_workload:
            raise PreconditionNotMetError(
                f"Attorney {panel_entry.name} has reached maximum workload limit "
                f"({panel_entry.max_workload})."
            )

        # Conflict of interest check (BR-PMS-044)
        coinventor_ids = list(app.coinventors.values_list("user_id", flat=True))
        if attorney_user_id == app.applicant_user_id or attorney_user_id in coinventor_ids:
            raise ConflictOfInterestError(
                "Attorney cannot represent an application in which they are "
                "an inventor (BR-PMS-044)."
            )

        app.assigned_attorney_user_id = attorney_user_id
        app.save(update_fields=["assigned_attorney_user_id", "updated_at"])

        # Mark any previous assignments inactive
        AttorneyAssignment.objects.filter(application=app).update(is_active=False)

        assignment = AttorneyAssignment.objects.create(
            application=app,
            attorney_user_id=attorney_user_id,
            assigned_by_user_id=assigned_by_user_id,
            status="offered",
            is_active=True,
        )

        log_audit(
            application=app,
            actor_user_id=assigned_by_user_id,
            action_type="attorney_assignment_offered",
            details={
                "attorney_user_id": attorney_user_id,
                "assignment_id": assignment.id,
                "assignment_status": assignment.status,
            },
        )

        enqueue_notification(
            topic="attorney.assigned",
            dedupe_key=f"pms:atty:assign:{app.id}:{assignment.id}",
            subject=f"PMS: Attorney Assignment Offered ({app.application_no})",
            body=(
                f"You have been offered the assignment for patent application "
                f"'{app.title}'. Please accept or decline."
            ),
            recipient_user_id=attorney_user_id,
        )

    return assignment


def respond_to_attorney_assignment(
    *,
    assignment_id: int,
    attorney_user_id: int,
    accept: bool,
    decline_reason: str = "",
) -> AttorneyAssignment:
    """Accept or decline an attorney assignment offer (UC-PMS-011, CFR-PMS-009)."""
    with transaction.atomic():
        assignment = AttorneyAssignment.objects.select_for_update().get(pk=assignment_id)
        app = assignment.application

        if assignment.attorney_user_id != attorney_user_id:
            raise PreconditionNotMetError("You are not authorized to respond to this assignment.")

        if assignment.status != "offered":
            raise PreconditionNotMetError(
                f"Assignment is not in 'offered' status (current: {assignment.status})."
            )

        now = timezone.now()
        assignment.status = "accepted" if accept else "declined"
        assignment.decline_reason = decline_reason.strip() if not accept else ""
        assignment.decided_at = now
        assignment.save()

        if not accept:
            app.assigned_attorney_user_id = None
        app.save(update_fields=["assigned_attorney_user_id", "updated_at"])

        # Update panel workload if accepted
        if accept:
            panel_entry = AttorneyPanel.objects.filter(attorney_user_id=attorney_user_id).first()
            if panel_entry:
                panel_entry.current_workload += 1
                panel_entry.save(update_fields=["current_workload", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="attorney_assignment_responded",
            details={
                "accepted": accept,
                "reason": decline_reason,
                "assignment_id": assignment.id,
                "assignment_status": assignment.status,
            },
        )

        enqueue_notification(
            topic="attorney.responded",
            dedupe_key=f"pms:atty:resp:{assignment.id}",
            subject=(
                f"PMS: Attorney Assignment {'Accepted' if accept else 'Declined'} "
                f"({app.application_no})"
            ),
            body=(
                f"Attorney {attorney_user_id} has "
                f"{'accepted' if accept else 'declined'} the assignment for '{app.title}'."
            ),
            recipient_user_id=assignment.assigned_by_user_id,
        )

    return assignment


def submit_patentability_assessment(
    *,
    application_id: int,
    attorney_user_id: int,
    recommendation: str,
    opinion_text: str,
    novelty_score: int = 0,
    non_obviousness_score: int = 0,
    utility_score: int = 0,
) -> PatentabilityAssessment:
    """Record an official patentability assessment and recommendation (UC-PMS-012, CFR-PMS-010)."""
    validate_patentability_opinion(recommendation, opinion_text)

    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        assessment = PatentabilityAssessment.objects.create(
            application=app,
            attorney_user_id=attorney_user_id,
            novelty_score=novelty_score,
            non_obviousness_score=non_obviousness_score,
            utility_score=utility_score,
            recommendation=recommendation,
            opinion_text=opinion_text.strip(),
            is_final=True,
        )

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="patentability_assessed",
            details={
                "recommendation": recommendation,
                "novelty": novelty_score,
                "non_obviousness": non_obviousness_score,
                "utility": utility_score,
            },
        )

    return assessment


def record_legal_advice(
    *,
    application_id: int,
    attorney_user_id: int,
    stage: str,
    advice_text: str,
) -> PatentLegalAdvice:
    """Record formal legal advice throughout the patent lifecycle (UC-PMS-033, CFR-PMS-004)."""
    if not advice_text or not advice_text.strip():
        raise PreconditionNotMetError("Legal advice text is required.")

    with transaction.atomic():
        app = PatentApplication.objects.get(pk=application_id)
        advice = PatentLegalAdvice.objects.create(
            application=app,
            attorney_user_id=attorney_user_id,
            stage=stage.strip(),
            advice_text=advice_text.strip(),
        )

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="legal_advice_recorded",
            details={"stage": stage},
        )

    return advice
