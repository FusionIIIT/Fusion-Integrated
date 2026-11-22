"""Transactional MMS lifecycle operations."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.mms.domain.policies import PolicyViolation, next_calendar_day, validate_rebate
from modules.mms.models import (
    RebateRequest,
    RoleAssignment,
    RoleSlot,
    SpecialFoodRequest,
    StudentRegistration,
    VacationResponse,
)


@transaction.atomic
def decide_registration(*, request_id: int, actor_id: int, approve: bool) -> StudentRegistration:
    request = StudentRegistration.objects.select_for_update().get(pk=request_id)
    if request.status != StudentRegistration.Status.PENDING:
        raise ConflictError(
            "Only pending registration requests can be decided.", code="request_not_pending"
        )
    request.decided_at = timezone.now()
    request.decided_by_user_id = actor_id
    if request.request_type == "deregister":
        request.status = (
            StudentRegistration.Status.DEREGISTERED
            if approve
            else StudentRegistration.Status.REJECTED
        )
        request.effective_date = next_calendar_day(timezone.localdate()) if approve else None
        if approve:
            current = (
                StudentRegistration.objects.select_for_update()
                .filter(
                    user_id=request.user_id,
                    cycle=request.cycle,
                    request_type="register",
                    status=StudentRegistration.Status.REGISTERED,
                )
                .order_by("-submitted_at")
                .first()
            )
            if current is not None:
                current.status = StudentRegistration.Status.DEREGISTERED
                current.effective_date = request.effective_date
                current.save(update_fields=["status", "effective_date"])
    else:
        request.status = (
            StudentRegistration.Status.REGISTERED
            if approve
            else StudentRegistration.Status.REJECTED
        )
    request.save(update_fields=["status", "decided_at", "decided_by_user_id", "effective_date"])
    return request


@transaction.atomic
def submit_rebate(
    *, actor_id: int, reason: str, explanation: str, start_date, end_date
) -> RebateRequest:
    overlap = (
        RebateRequest.objects.filter(
            user_id=actor_id,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        .exclude(status=RebateRequest.Status.REJECTED)
        .exists()
    )
    try:
        validate_rebate(
            start_date=start_date,
            end_date=end_date,
            submitted_on=timezone.localdate(),
            reason=reason,
            explanation=explanation,
            overlapping=overlap,
        )
    except PolicyViolation as exc:
        from core.api.exceptions import BadRequestError

        raise BadRequestError(str(exc), code="mms_policy_violation") from exc
    return RebateRequest.objects.create(
        user_id=actor_id,
        reason=reason,
        explanation=explanation,
        start_date=start_date,
        end_date=end_date,
    )


@transaction.atomic
def assign_role(*, role: str, user_id: int, actor_id: int, ends_at) -> RoleAssignment:
    now = timezone.now()
    if ends_at is not None and ends_at <= now:
        from core.api.exceptions import BadRequestError

        raise BadRequestError("Role end must follow its start.", code="invalid_role_period")
    RoleSlot.objects.get_or_create(role=role)
    RoleSlot.objects.select_for_update().get(role=role)
    current = (
        RoleAssignment.objects.select_for_update()
        .filter(
            role=role,
            starts_at__lte=now,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("-starts_at")
        .first()
    )
    if current is not None:
        current.ends_at = now
        current.save(update_fields=["ends_at"])
    return RoleAssignment.objects.create(
        role=role, user_id=user_id, starts_at=now, ends_at=ends_at, recorded_by_user_id=actor_id
    )


@transaction.atomic
def decide_rebate(*, request_id: int, actor_id: int, approve: bool) -> RebateRequest:
    row = RebateRequest.objects.select_for_update().get(pk=request_id)
    if row.status != RebateRequest.Status.PENDING:
        raise ConflictError("Only pending rebates can be decided.", code="request_not_pending")
    row.status = RebateRequest.Status.APPROVED if approve else RebateRequest.Status.REJECTED
    row.decided_at = timezone.now()
    row.decided_by_user_id = actor_id
    row.save(update_fields=["status", "decided_at", "decided_by_user_id"])
    return row


@transaction.atomic
def decide_special_food(*, request_id: int, actor_id: int, approve: bool) -> SpecialFoodRequest:
    row = SpecialFoodRequest.objects.select_for_update().get(pk=request_id)
    if row.status != SpecialFoodRequest.Status.REQUESTED:
        raise ConflictError(
            "Only requested special food can be decided.", code="request_not_pending"
        )
    row.status = (
        SpecialFoodRequest.Status.APPROVED if approve else SpecialFoodRequest.Status.REJECTED
    )
    row.decided_at = timezone.now()
    row.decided_by_user_id = actor_id
    row.save(update_fields=["status", "decided_at", "decided_by_user_id"])
    return row


@transaction.atomic
def update_special_fulfillment(*, request_id: int, outcome: str) -> SpecialFoodRequest:
    row = SpecialFoodRequest.objects.select_for_update().get(pk=request_id)
    if row.status != SpecialFoodRequest.Status.APPROVED:
        raise ConflictError(
            "Only approved special food can be fulfilled or cancelled.", code="request_not_approved"
        )
    row.status = outcome
    row.save(update_fields=["status"])
    return row


@transaction.atomic
def respond_to_survey(*, survey_id: int, actor_id: int, response: str) -> VacationResponse:
    row = VacationResponse.objects.select_for_update().get(survey_id=survey_id, user_id=actor_id)
    if timezone.now() >= row.survey.response_deadline:
        from core.api.exceptions import BadRequestError

        raise BadRequestError("The response deadline has passed.", code="survey_closed")
    if row.response is not None:
        from core.api.exceptions import BadRequestError

        raise BadRequestError("A response has already been recorded.", code="response_recorded")
    row.response = response
    row.responded_at = timezone.now()
    row.save(update_fields=["response", "responded_at"])
    return row


@transaction.atomic
def apply_vacation_defaults() -> int:
    """Apply the specified No default after each outstanding survey deadline."""
    now = timezone.now()
    outstanding = list(
        VacationResponse.objects.select_for_update().filter(
            response__isnull=True,
            survey__response_deadline__lte=now,
        )
    )
    for row in outstanding:
        row.response = "no"
        row.defaulted = True
        row.responded_at = now
    VacationResponse.objects.bulk_update(outstanding, ["response", "defaulted", "responded_at"])
    return len(outstanding)
