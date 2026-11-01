
"""Core ELM transitions with balance validation and atomic updates."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from modules.elm.models import (
    LeaveRequest,
    LeavePolicy,
    LeaveAccount,
    LeaveTransaction,
)


PENDING = {
    "awaiting_substitute_response",
    "applicant_action_required",
    "awaiting_unit_head_review",
    "awaiting_establishment_routing",
    "awaiting_final_sanction_decision",
    "awaiting_director_self_sanction",
}


def _get_locked_account(user_id, category, year, entitlement):
    """Get or initialize an account and lock it for updates."""
    account, _ = LeaveAccount.objects.get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={"balance": entitlement},
    )

    return LeaveAccount.objects.select_for_update().get(pk=account.pk)


def _deduct_leave_balance(request_obj, actor):
    """Deduct approved leave exactly once."""
    existing = LeaveTransaction.objects.filter(
        request=request_obj,
        transaction_type="leave_approved",
    ).exists()

    if existing:
        return

    policy = LeavePolicy.objects.filter(
        category=request_obj.category,
        enabled=True,
    ).first()

    if policy is None:
        raise ValidationError({
            "category": "Leave policy is not configured."
        })

    account = _get_locked_account(
        request_obj.user_id,
        request_obj.category,
        request_obj.start_date.year,
        policy.annual_entitlement,
    )

    amount = Decimal(str(request_obj.days))

    if account.balance < amount:
        raise ValidationError({
            "balance": (
                f"Insufficient {request_obj.category} leave balance. "
                f"Available: {account.balance}, required: {amount}."
            )
        })

    account.balance -= amount
    account.save(update_fields=["balance", "updated_at"])

    LeaveTransaction.objects.create(
        account=account,
        request=request_obj,
        amount=-amount,
        transaction_type="leave_approved",
        actor_user_id=getattr(actor, "user_id", None),
    )


@transaction.atomic
def submit(*, actor, data):
    start = data["start_date"]
    end = data["end_date"]

    if end < start:
        raise ValidationError({
            "end_date": "End date must be on or after start date."
        })

    if start < timezone.localdate():
        raise ValidationError({
            "start_date": "Leave cannot start in the past."
        })

    category = data["category"]

    policy = LeavePolicy.objects.filter(
        category=category,
        enabled=True,
    ).first()

    if policy is None:
        raise ValidationError({
            "category": "Leave category is not configured."
        })

    overlapping = LeaveRequest.objects.filter(
        user_id=actor.user_id,
        status__in=PENDING | {"approved", "extension_pending"},
        start_date__lte=end,
        end_date__gte=start,
    ).exists()

    if overlapping:
        raise ValidationError({
            "dates": "Leave overlaps an existing pending or approved request."
        })

    substitute_id = data.get("substitute_user_id")

    if policy.requires_substitute and not substitute_id:
        raise ValidationError({
            "substitute_user_id": "A substitute is required."
        })

    if substitute_id and substitute_id == actor.user_id:
        raise ValidationError({
            "substitute_user_id": "You cannot nominate yourself as substitute."
        })

    days = Decimal((end - start).days + 1)

    # Lock the account so simultaneous applications cannot overbook it.
    account = _get_locked_account(
        actor.user_id,
        category,
        start.year,
        policy.annual_entitlement,
    )

    # Pending requests reserve balance logically.
    pending_days = LeaveRequest.objects.filter(
        user_id=actor.user_id,
        category=category,
        start_date__year=start.year,
        status__in=PENDING,
    ).aggregate(total=Sum("days"))["total"] or Decimal("0")

    available = account.balance - pending_days

    if available < days:
        raise ValidationError({
            "balance": (
                f"Insufficient {category} leave balance. "
                f"Available after pending requests: {available}, "
                f"requested: {days}."
            )
        })

    obj = LeaveRequest.objects.create(
        user_id=actor.user_id,
        category=category,
        start_date=start,
        end_date=end,
        days=days,
        purpose=data["purpose"],
        station_leave=data.get("station_leave", {}),
        substitute_user_id=substitute_id,
        status=(
            "awaiting_substitute_response"
            if policy.requires_substitute
            else "awaiting_unit_head_review"
        ),
    )

    return obj


@transaction.atomic
def transition(*, request_obj, actor, action, reason=""):
    # Lock the request to prevent simultaneous state transitions.
    obj = LeaveRequest.objects.select_for_update().get(
        pk=request_obj.pk
    )

    old = obj.status

    if action == "withdraw":
        if actor.user_id != obj.user_id or old not in PENDING:
            raise PermissionDenied(
                "Only the applicant can withdraw a pending request."
            )

        obj.status = "withdrawn"

    elif action in ("accept_substitute", "decline_substitute"):
        if (
            actor.user_id != obj.substitute_user_id
            or old != "awaiting_substitute_response"
        ):
            raise PermissionDenied(
                "This substitute response is not assigned to you."
            )

        obj.substitute_decision = (
            "accept" if action == "accept_substitute" else "decline"
        )

        obj.status = (
            "awaiting_unit_head_review"
            if action == "accept_substitute"
            else "applicant_action_required"
        )

    elif action in ("approve", "not_recommended"):
        if old != "awaiting_unit_head_review":
            raise ValidationError(
                "Request is not awaiting Unit Head review."
            )

        obj.unit_head_decision = action

        policy = LeavePolicy.objects.filter(
            category=obj.category,
            enabled=True,
        ).first()

        if policy is None:
            raise ValidationError("Leave policy is not configured.")

        if policy.higher_sanction:
            obj.status = "awaiting_final_sanction_decision"
        else:
            obj.status = (
                "approved" if action == "approve" else "rejected"
            )

    elif action in ("final_approve", "final_reject"):
        if old not in (
            "awaiting_final_sanction_decision",
            "awaiting_director_self_sanction",
        ):
            raise ValidationError(
                "Request is not awaiting final sanction."
            )

        obj.final_decision = (
            "approve" if action == "final_approve" else "reject"
        )

        obj.status = (
            "approved" if action == "final_approve" else "rejected"
        )

    else:
        raise ValidationError({
            "action": "Unsupported workflow action."
        })

    obj.decision_reason = reason
    obj.version += 1

    # Deduct before saving approval. Both operations roll back together
    # if balance validation or transaction creation fails.
    if obj.status == "approved":
        _deduct_leave_balance(obj, actor)

    obj.save(update_fields=[
        "status",
        "substitute_decision",
        "unit_head_decision",
        "final_decision",
        "decision_reason",
        "version",
        "updated_at",
    ])

    return obj
