from datetime import date, datetime
from django.db import transaction

from modules.pms.domain.business_rules import verify_appeal_eligibility
from modules.pms.domain.state_machine import PatentStateMachine
from modules.pms.domain.validation import validate_no_conflict_of_interest
from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.models.reviews import InternalReview, ReviewVerdict
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def assign_director(
    app_id: int,
    coordinator_user_id: int,
    director_user_id: int,
    roles: list[str],
) -> PatentApplication:
    """Assign director / scrutiny reviewer to an application (BR-PMS-022, BR-PMS-025)."""
    app = get_application_scoped(app_id, coordinator_user_id, roles)

    # Conflict of interest check (BR-PMS-025)
    inventor_ids = list(app.inventors.values_list("user_id", flat=True))
    validate_no_conflict_of_interest(app.applicant_user_id, director_user_id, inventor_ids)

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="ASSIGN_DIRECTOR",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.assigned_director_id = director_user_id
    app.save(update_fields=["status", "assigned_director_id", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="ASSIGN_DIRECTOR",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=coordinator_user_id,
        payload={"assigned_director_id": director_user_id},
    )

    return app


@transaction.atomic
def submit_review(
    app_id: int,
    reviewer_user_id: int,
    verdict: str,
    comments: str,
    scores: dict[str, int],
    roles: list[str],
) -> InternalReview:
    """Submit institutional review and advance application workflow (BW-PMS-01, BW-PMS-02)."""
    app = get_application_scoped(app_id, reviewer_user_id, roles)

    review = InternalReview.objects.create(
        application=app,
        reviewer_user_id=reviewer_user_id,
        verdict=verdict,
        comments=comments,
        novelty_score=scores.get("novelty", 5),
        inventive_step_score=scores.get("inventive_step", 5),
        commercial_viability_score=scores.get("commercial", 5),
    )

    # Determine event based on verdict
    if verdict == ReviewVerdict.RECOMMEND_APPROVAL:
        event = "APPROVE"
    elif verdict == ReviewVerdict.RECOMMEND_REVISION:
        event = "REQUEST_REVISION"
    else:
        event = "REJECT"

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event=event,
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name=f"REVIEW_{event}",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=reviewer_user_id,
        payload={"verdict": verdict, "review_id": review.id},
    )

    return review


@transaction.atomic
def file_appeal(
    app_id: int,
    applicant_user_id: int,
    appeal_statement: str,
    roles: list[str],
) -> PatentApplication:
    """File appeal against institutional rejection within 30 days (BR-PMS-038)."""
    app = get_application_scoped(app_id, applicant_user_id, roles)

    # Verify appeal timing (BR-PMS-038)
    rejection_event = app.audit_events.filter(to_status=ApplicationStatus.REJECTED).first()
    rejection_date = rejection_event.created_at.date() if rejection_event else app.updated_at.date()
    verify_appeal_eligibility(rejection_date, date.today())

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="APPEAL",
        actor_roles=roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="FILE_APPEAL",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=applicant_user_id,
        payload={"statement": appeal_statement},
    )

    return app
