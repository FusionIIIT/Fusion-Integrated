"""Director assignment and review services (BW-PMS-01..05, CW-PMS-01)."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_DIRECTOR,
    ACTOR_PCC_ADMIN,
    DECISION_APPROVE,
    DECISION_NEEDS_REVISION,
    DECISION_REJECT,
    REVIEW_WINDOW_BUSINESS_DAYS,
    REVISION_WINDOW_DAYS,
    STATUS_APPROVED,
    STATUS_NEEDS_REVISION,
    STATUS_REJECTED,
    STATUS_UNDER_REVIEW,
)
from modules.pms.domain.rules import (
    check_director_conflict_of_interest,
    check_pcc_admin_conflict_of_interest,
    validate_director_review_decision,
)
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    DeadlineTracking,
    DirectorAssignment,
    DirectorReview,
    PatentApplication,
)
from modules.pms.services.audit import record_audit_event


def calculate_business_days_deadline(start_date, business_days: int):
    """Add N business days (skipping Saturday and Sunday)."""
    current = start_date
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday to Friday
            added += 1
    return current


@transaction.atomic
def assign_director_to_application(
    application: PatentApplication,
    director_user_id: int,
    assigned_by_user_id: int,
) -> DirectorAssignment:
    """Assign an application to a Director for technical review (UC-PMS-007, BW-PMS-01)."""
    # 1. Conflict of interest checks
    inventor_ids = list(
        application.inventors.filter(user_id__isnull=False).values_list("user_id", flat=True)
    )
    if application.user_id:
        inventor_ids.append(application.user_id)

    check_director_conflict_of_interest(director_user_id, inventor_ids)
    check_pcc_admin_conflict_of_interest(assigned_by_user_id, inventor_ids)

    # 2. State transition check: e.g. Submitted -> Under Review
    validate_transition(application.status, STATUS_UNDER_REVIEW, ACTOR_PCC_ADMIN)

    prev_status = application.status
    application.status = STATUS_UNDER_REVIEW
    application.save()

    # 3. Create or update assignment with 15 business days deadline (BR-PMS-031)
    due_date = calculate_business_days_deadline(timezone.now(), REVIEW_WINDOW_BUSINESS_DAYS)
    assignment = DirectorAssignment.objects.create(
        application=application,
        director_user_id=director_user_id,
        assigned_by_user_id=assigned_by_user_id,
        due_at=due_date,
        status="assigned",
    )

    # 4. Schedule deadline tracking
    DeadlineTracking.objects.create(
        application=application,
        deadline_type="director_review",
        due_date=due_date,
    )

    # 5. Audit log
    record_audit_event(
        application=application,
        user_id=assigned_by_user_id,
        actor_role=ACTOR_PCC_ADMIN,
        action_type="assign_director",
        previous_state=prev_status,
        new_state=STATUS_UNDER_REVIEW,
        details={"director_user_id": director_user_id, "due_date": due_date.isoformat()},
    )

    return assignment


@transaction.atomic
def record_director_review(
    application: PatentApplication,
    director_user_id: int,
    decision: str,
    justification: str,
) -> DirectorReview:
    """Record Director technical evaluation and decision (UC-PMS-008, BW-PMS-01..05)."""
    # 1. Validate decision and >= 50 chars justification (BR-PMS-029, 030)
    validate_director_review_decision(decision, justification)

    # 2. Map decision to target lifecycle state
    target_status = {
        DECISION_APPROVE: STATUS_APPROVED,
        DECISION_REJECT: STATUS_REJECTED,
        DECISION_NEEDS_REVISION: STATUS_NEEDS_REVISION,
    }[decision]

    # 3. State transition check
    validate_transition(application.status, target_status, ACTOR_DIRECTOR)

    prev_status = application.status
    application.status = target_status

    if decision == DECISION_NEEDS_REVISION:
        # 60 days revision window (BR-PMS-035)
        application.revision_deadline = timezone.now() + timedelta(days=REVISION_WINDOW_DAYS)
        DeadlineTracking.objects.create(
            application=application,
            deadline_type="revision",
            due_date=application.revision_deadline,
        )

    application.save()

    # 4. Mark assignment completed
    DirectorAssignment.objects.filter(
        application=application, director_user_id=director_user_id, status="assigned"
    ).update(status="completed")

    # 5. Create review record
    review = DirectorReview.objects.create(
        application=application,
        director_user_id=director_user_id,
        decision=decision,
        justification=justification.strip(),
    )

    # 6. Audit log
    record_audit_event(
        application=application,
        user_id=director_user_id,
        actor_role=ACTOR_DIRECTOR,
        action_type=f"review_{decision}",
        previous_state=prev_status,
        new_state=target_status,
        details={"justification": justification.strip()},
    )

    return review
