from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.hr.domain import state_machine
from modules.hr.models import (
    APPRAISAL_ARCHIVE_TYPE,
    Appraisal,
    AppraisalWindow,
    EmployeeRecord,
)
from modules.hr.services import authz, notifications
from modules.hr.services.common import audit


@transaction.atomic
def submit_appraisal(*, actor, period: str, form_data: dict) -> Appraisal:
    authz.require(actor, "hr.appraisal.create")
    if (
        EmployeeRecord.objects.filter(user_id=actor.user_id, employment_status="active").first()
        is None
    ):
        raise ConflictError(
            "An active employee service record is required to submit an appraisal.",
            code="employee_record_required",
        )
    now = timezone.now()
    window = AppraisalWindow.objects.filter(
        period=period,
        is_active=True,
        opens_at__lte=now,
        closes_at__gte=now,
    ).first()
    if window is None:
        raise ConflictError(
            "The appraisal submission window is not open.",
            code="appraisal_window_closed",
        )
    if not isinstance(form_data, dict) or not form_data:
        raise ConflictError(
            "Appraisal form information is required.", code="appraisal_data_required"
        )
    try:
        appraisal = Appraisal.objects.create(
            employee_user_id=actor.user_id, period=period, form_data=form_data
        )
    except IntegrityError as exc:
        raise ConflictError(
            "An appraisal for this period has already been submitted.",
            code="appraisal_already_submitted",
        ) from exc
    audit(
        actor=actor,
        entity_type="appraisal",
        entity_id=appraisal.pk,
        action="appraisal.submitted",
        details={"period": period},
    )
    notifications.enqueue(
        recipient_user_id=actor.user_id,
        topic="appraisal.submitted",
        dedupe_key=f"appraisal:{appraisal.pk}:submitted",
        subject="Yearly appraisal submitted",
        body=f"Your appraisal for {period} was submitted.",
        payload={"appraisal_id": appraisal.pk, "status": appraisal.status},
    )
    return appraisal


@transaction.atomic
def assign_reviewers(*, actor, appraisal_id: int, reviewer_user_ids: list[int]) -> Appraisal:
    authz.require(actor, "hr.appraisal.assign")
    appraisal = Appraisal.objects.select_for_update().filter(pk=appraisal_id).first()
    if appraisal is None:
        raise NotFoundError("No such appraisal.")
    try:
        state_machine.verify_appraisal_state(appraisal.status)
    except state_machine.InvalidTransition as exc:
        raise ConflictError(
            "Reviewers can only be assigned before appraisal review begins.",
            code="invalid_transition",
        ) from exc
    if not reviewer_user_ids or any(uid <= 0 for uid in reviewer_user_ids):
        raise ConflictError("At least one valid reviewer is required.", code="reviewers_required")
    if len(set(reviewer_user_ids)) != len(reviewer_user_ids):
        raise ConflictError("A reviewer may appear only once.", code="duplicate_appraisal_reviewer")
    if appraisal.employee_user_id in reviewer_user_ids:
        raise ConflictError(
            "An employee cannot review their own appraisal.", code="self_review_not_allowed"
        )
    people = directory.get_users(reviewer_user_ids)
    active_user_ids = directory.held_employee_ids()
    if (
        len(people) != len(set(reviewer_user_ids))
        or not set(reviewer_user_ids).issubset(active_user_ids)
        or any(people[uid].kind not in {"faculty", "staff"} for uid in reviewer_user_ids)
    ):
        raise ConflictError(
            "Appraisal reviewers must be active faculty or staff identities.",
            code="invalid_appraisal_reviewer",
        )

    appraisal.reviewer_user_ids = reviewer_user_ids
    appraisal.current_reviewer_index = 0
    appraisal.current_reviewer_user_id = reviewer_user_ids[0]
    appraisal.status = state_machine.PENDING_REVIEW
    appraisal.assigned_by_user_id = actor.user_id
    appraisal.save(
        update_fields=[
            "reviewer_user_ids",
            "current_reviewer_index",
            "status",
            "current_reviewer_user_id",
            "assigned_by_user_id",
            "updated_at",
        ]
    )
    audit(
        actor=actor,
        entity_type="appraisal",
        entity_id=appraisal.pk,
        action="appraisal.reviewers_assigned",
        details={"reviewer_user_ids": reviewer_user_ids},
    )
    for index, reviewer_id in enumerate(reviewer_user_ids):
        notifications.enqueue(
            recipient_user_id=reviewer_id,
            topic="appraisal.assigned",
            dedupe_key=f"appraisal:{appraisal.pk}:reviewer:{index}",
            subject="Appraisal assigned for review",
            body=f"An appraisal for {appraisal.period} is assigned to you.",
            payload={"appraisal_id": appraisal.pk, "status": appraisal.status},
        )
    return appraisal


@transaction.atomic
def review_appraisal(*, actor, appraisal_id: int, action: str, note: str = "") -> Appraisal:
    authz.require(actor, "hr.appraisal.review")
    appraisal = Appraisal.objects.select_for_update().filter(pk=appraisal_id).first()
    if appraisal is None:
        raise NotFoundError("No such appraisal.")
    reviewer_ids = appraisal.reviewer_user_ids
    index = appraisal.current_reviewer_index
    if not reviewer_ids or index >= len(reviewer_ids):
        raise ConflictError(
            "The appraisal review route is invalid.", code="invalid_appraisal_route"
        )
    if reviewer_ids[index] != actor.user_id or appraisal.employee_user_id == actor.user_id:
        raise NotFoundError("No such appraisal is assigned to you.")
    try:
        transition = state_machine.review_appraisal(
            appraisal.status,
            action=action,
            current_index=index,
            reviewer_count=len(reviewer_ids),
        )
    except state_machine.InvalidTransition as exc:
        code = (
            "workflow_order"
            if exc.action in {"finalization_must_follow_route", "no_next_reviewer"}
            else "invalid_transition"
        )
        raise ConflictError(
            "The requested review action is not valid at this step.",
            code=code,
        ) from exc

    before = appraisal.status
    reviews = [
        *appraisal.reviews,
        {
            "reviewer_user_id": actor.user_id,
            "action": action,
            "note": (note or "").strip(),
            "at": timezone.now().isoformat(),
        },
    ]
    appraisal.status = transition.state
    appraisal.current_reviewer_index = transition.authority_step
    appraisal.reviews = reviews
    appraisal.current_reviewer_user_id = (
        reviewer_ids[transition.authority_step] if action == "forward" else None
    )
    touched = [
        "status",
        "current_reviewer_index",
        "current_reviewer_user_id",
        "reviews",
        "updated_at",
    ]
    if action == "finalize":
        appraisal.finalized_at = timezone.now()
        touched.append("finalized_at")
        employee_record = (
            EmployeeRecord.objects.select_for_update()
            .filter(
                user_id=appraisal.employee_user_id,
            )
            .first()
        )
        if employee_record is None:
            raise ConflictError(
                "The employee service record is unavailable; contact HR before finalizing.",
                code="employee_record_required",
            )
        employee_record.service_history = [
            *employee_record.service_history,
            {
                "record_type": APPRAISAL_ARCHIVE_TYPE,
                "appraisal_id": appraisal.pk,
                "period": appraisal.period,
                "finalized_at": appraisal.finalized_at.isoformat(),
            },
        ]
        employee_record.save(update_fields=["service_history", "updated_at"])
    appraisal.save(update_fields=touched)
    audit(
        actor=actor,
        entity_type="appraisal",
        entity_id=appraisal.pk,
        action=f"appraisal.{action}",
        details={
            "from_status": before,
            "to_status": appraisal.status,
            "note": (note or "").strip(),
        },
    )

    if action == "forward":
        next_reviewer = reviewer_ids[transition.authority_step]
        notifications.enqueue(
            recipient_user_id=next_reviewer,
            topic="appraisal.forwarded",
            dedupe_key=f"appraisal:{appraisal.pk}:reviewer:{transition.authority_step}",
            subject="Appraisal forwarded for review",
            body=f"An appraisal for {appraisal.period} is assigned to you.",
            payload={"appraisal_id": appraisal.pk, "status": appraisal.status},
        )
    else:
        notifications.enqueue(
            recipient_user_id=appraisal.employee_user_id,
            topic="appraisal.finalized",
            dedupe_key=f"appraisal:{appraisal.pk}:finalized",
            subject="Yearly appraisal finalized",
            body=f"Your appraisal for {appraisal.period} was finalized.",
            payload={"appraisal_id": appraisal.pk, "status": appraisal.status},
        )
    return appraisal
