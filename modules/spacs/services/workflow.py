from collections.abc import Mapping
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.domain.state_machine import (
    SCHOLARSHIP_APPLICATION,
    ActorNotAllowed,
    AmbiguousTransition,
    InvalidTransition,
    Transition,
    resolve,
)
from modules.spacs.models import (
    Application,
    ApplicationReview,
    ApplicationTransition,
    AuditEvent,
    NotificationOutbox,
    WorkflowTask,
)

ASSISTANT = "SPACS Assistant"
CONVENER = "SPACS Convener"


def _application(*, public_id: UUID) -> Application:
    application = (
        Application.objects.select_for_update()
        .select_related("catalogue_version")
        .filter(public_id=public_id)
        .first()
    )
    if application is None:
        raise NotFoundError("No such application.")
    return application


def _task_for_actor(
    *,
    application: Application,
    role_name: str,
    user_id: int,
) -> WorkflowTask:
    task = (
        WorkflowTask.objects.select_for_update()
        .filter(
            application=application,
            role_name=role_name,
            completed_at__isnull=True,
        )
        .filter(assigned_user_id__isnull=True)
        .first()
    )
    if task is None:
        task = (
            WorkflowTask.objects.select_for_update()
            .filter(
                application=application,
                role_name=role_name,
                assigned_user_id=user_id,
                completed_at__isnull=True,
            )
            .first()
        )
    if task is None:
        raise ConflictError(
            "No pending task is available for this role.",
            code="workflow_task_unavailable",
        )
    return task


def _close_task(*, task: WorkflowTask, reason: str) -> None:
    task.completed_at = timezone.now()
    task.closed_reason = reason
    task.save(update_fields=["completed_at", "closed_reason", "updated_at"])


def _notify_owner(
    *,
    application: Application,
    transition: ApplicationTransition,
) -> None:
    NotificationOutbox.objects.get_or_create(
        dedupe_key=(
            f"application:{application.public_id}:transition:{transition.pk}:user:in_dashboard"
        ),
        defaults={
            "topic": "application.workflow_transition",
            "channel": "in_dashboard",
            "recipient_user_id": application.user_id,
            "payload": {
                "application_id": str(application.public_id),
                "state": transition.to_state,
            },
        },
    )
    NotificationOutbox.objects.get_or_create(
        dedupe_key=(f"application:{application.public_id}:transition:{transition.pk}:user:email"),
        defaults={
            "topic": "application.workflow_transition",
            "channel": "email",
            "recipient_user_id": application.user_id,
            "subject": "Scholarship application update",
            "body": (f"Your scholarship application is now in state: {transition.to_state}."),
            "payload": {
                "application_id": str(application.public_id),
                "state": transition.to_state,
            },
        },
    )


def _record_transition(
    *,
    application: Application,
    transition: Transition,
    actor_user_id: int,
    reason: str = "",
    record_guard_as_reason: bool = True,
) -> ApplicationTransition:
    previous_state = application.state
    recorded_reason = reason.strip()
    if not recorded_reason and record_guard_as_reason:
        recorded_reason = transition.guard
    application.state = transition.to
    application.save(update_fields=["state", "updated_at"])
    row = ApplicationTransition.objects.create(
        application=application,
        from_state=previous_state,
        to_state=transition.to,
        actor_user_id=actor_user_id,
        actor_label=transition.actor,
        reason=recorded_reason,
    )
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type="application.state_changed",
        actor_user_id=actor_user_id,
        actor_label=transition.actor,
        payload={
            "from_state": previous_state,
            "to_state": transition.to,
            "guard": transition.guard,
            "reason": recorded_reason,
        },
    )
    _notify_owner(application=application, transition=row)
    return row


def _transition(
    *,
    application: Application,
    to_state: str,
    actor: str,
    guard: str,
) -> Transition:
    try:
        return resolve(
            SCHOLARSHIP_APPLICATION,
            application.state,
            to_state,
            actor,
            guard,
        )
    except (ActorNotAllowed, AmbiguousTransition, InvalidTransition) as error:
        raise ConflictError(
            "The application cannot move to the requested workflow state.",
            code="invalid_application_transition",
        ) from error


@transaction.atomic
def begin_verification(*, public_id: UUID, user_id: int) -> Application:
    application = _application(public_id=public_id)
    _task_for_actor(
        application=application,
        role_name=ASSISTANT,
        user_id=user_id,
    )
    transition = _transition(
        application=application,
        to_state="Under Verification",
        actor=ASSISTANT,
        guard="Assistant opens assigned verification",
    )
    _record_transition(
        application=application,
        transition=transition,
        actor_user_id=user_id,
    )
    return application


@transaction.atomic
def record_findings(
    *,
    public_id: UUID,
    reviewer_user_id: int,
    findings: Mapping[str, object],
) -> ApplicationReview:
    if not isinstance(findings, Mapping):
        raise BadRequestError(
            "Review findings must be an object.",
            code="invalid_review_findings",
        )
    application = _application(public_id=public_id)
    if application.state != "Under Verification":
        raise ConflictError(
            "Review findings can only be recorded during verification.",
            code="application_not_under_verification",
        )
    _task_for_actor(
        application=application,
        role_name=ASSISTANT,
        user_id=reviewer_user_id,
    )
    review = ApplicationReview.objects.create(
        application=application,
        reviewer_user_id=reviewer_user_id,
        findings=dict(findings),
    )
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type="application.review_findings_recorded",
        actor_user_id=reviewer_user_id,
        actor_label=ASSISTANT,
        payload={"review_id": review.pk, "finding_keys": sorted(findings)},
    )
    return review


@transaction.atomic
def request_correction(
    *,
    public_id: UUID,
    user_id: int,
    reason: str,
    actor: str = ASSISTANT,
) -> Application:
    if not isinstance(reason, str) or not reason.strip():
        raise BadRequestError(
            "A reason is required to request correction.",
            code="reason_required",
        )
    if actor not in {ASSISTANT, CONVENER}:
        raise BadRequestError("Unsupported workflow actor.")
    application = _application(public_id=public_id)
    task = _task_for_actor(
        application=application,
        role_name=actor,
        user_id=user_id,
    )
    transition = _transition(
        application=application,
        to_state="Correction Required",
        actor=actor,
        guard=("Correction required" if actor == ASSISTANT else "Return for correction"),
    )
    _record_transition(
        application=application,
        transition=transition,
        actor_user_id=user_id,
        reason=reason,
    )
    _close_task(task=task, reason="Correction Required")
    return application


@transaction.atomic
def route_verification(
    *,
    public_id: UUID,
    user_id: int,
    concern: bool = False,
) -> Application:
    application = _application(public_id=public_id)
    task = _task_for_actor(
        application=application,
        role_name=ASSISTANT,
        user_id=user_id,
    )
    to_state = "Verification Concern / Routed" if concern else "Verified / Routed for Decision"
    guard = (
        "Unresolved concern requiring decision"
        if concern
        else (
            "Reverification satisfied"
            if application.state == "Resubmitted"
            else "Verification satisfied"
        )
    )
    transition = _transition(
        application=application,
        to_state=to_state,
        actor=ASSISTANT,
        guard=guard,
    )
    _record_transition(
        application=application,
        transition=transition,
        actor_user_id=user_id,
    )
    _close_task(task=task, reason=to_state)
    WorkflowTask.objects.create(application=application, role_name=CONVENER)
    return application


@transaction.atomic
def begin_convener_review(*, public_id: UUID, user_id: int) -> Application:
    application = _application(public_id=public_id)
    _task_for_actor(
        application=application,
        role_name=CONVENER,
        user_id=user_id,
    )
    transition = _transition(
        application=application,
        to_state="Under Convener Review",
        actor=CONVENER,
        guard="Open decision task",
    )
    _record_transition(
        application=application,
        transition=transition,
        actor_user_id=user_id,
    )
    return application


@transaction.atomic
def decide(
    *,
    public_id: UUID,
    user_id: int,
    outcome: str,
    reason: str = "",
) -> Application:
    if outcome not in {"Approved", "Rejected"}:
        raise BadRequestError("Unsupported scholarship decision.")
    if not isinstance(reason, str):
        raise BadRequestError("The decision reason must be text.")
    application = _application(public_id=public_id)
    task = _task_for_actor(
        application=application,
        role_name=CONVENER,
        user_id=user_id,
    )
    transition = _transition(
        application=application,
        to_state=outcome,
        actor=CONVENER,
        guard="Approve" if outcome == "Approved" else "Reject",
    )
    _record_transition(
        application=application,
        transition=transition,
        actor_user_id=user_id,
        reason=reason,
        record_guard_as_reason=False,
    )
    _close_task(task=task, reason=outcome)
    return application
