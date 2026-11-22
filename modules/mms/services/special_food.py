"""Special food requests (BR-MMS-028/029/030/031; UC-019/020/021/029;
BW-MMS-11..15, CW-MMS-05)."""

from __future__ import annotations

import contextlib
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import rules
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, GuardFailed, InvalidTransition
from modules.mms.models import (
    SpecialFoodCharge,
    SpecialFoodPolicy,
    SpecialFoodRequest,
    SpecialFoodTransition,
)
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def _decision_period_hours(now=None) -> int:
    """Institution-defined decision period from the effective-dated policy.

    No seeded row → the module is not ready; surface a clear error rather
    than inventing a value (ISS-MMS-013).
    """
    now = now or timezone.now()
    today = now.date()
    policy = (
        SpecialFoodPolicy.objects.filter(is_active=True, effective_from__lte=today)
        .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=today))
        .first()
    )
    if policy is None:
        raise ConflictError(
            "Special food decision period is not configured. An "
            "administrator must seed the special food policy before requests "
            "can be submitted."
        )
    return policy.decision_period_hours


def submit(actor, reason: str, requested_date) -> SpecialFoodRequest:
    """BR-MMS-028: validate lead time, record Requested, submission
    notification."""
    authz.require(actor, "mms.special_food.create")
    own = actor.user_id
    submitted_on = timezone.localdate()
    try:
        rules.special_food_lead_time_ok(submitted_on, requested_date)
    except GuardFailed as exc:
        raise ConflictError(exc.message) from exc
    period_hours = _decision_period_hours()
    decision_due_at = timezone.now() + timezone.timedelta(hours=period_hours)
    with transaction.atomic():
        req = SpecialFoodRequest.objects.create(
            user_id=own,
            reason=reason,
            requested_date=requested_date,
            status="requested",
            decision_due_at=decision_due_at,
            submitted_at=timezone.now(),
        )
        with contextlib.suppress(InvalidTransition):
            sm.resolve("no_request", "requested", sm.STUDENT)
        notifications.enqueue(
            topic="special_food.submitted",
            dedupe_key=f"special_food.submitted:u{own}:{req.pk}",
            subject="Special food request received",
            body=f"Your special food request ({req.pk}) for "
            f"{requested_date} has been recorded and is awaiting "
            f"Caretaker decision.",
            recipient_user_id=own,
        )
    return req


def decide(actor, pk: int, approve: bool, note: str = "") -> SpecialFoodRequest:
    """BR-MMS-029/031: Caretaker approves or rejects a Requested request
    within the decision period; no second decision once decided."""
    authz.require(actor, "mms.special_food.review")
    to_status = "approved" if approve else "rejected"
    try:
        sm.resolve("requested", to_status, sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        req = (
            scoping.special_food_requests_for(actor)
            .filter(pk=pk, status="requested")
            .select_for_update()
            .first()
        )
        if req is None:
            raise NotFoundError(
                "No Requested special food request with that id, or it has already been decided."
            )
        now = timezone.now()
        if req.decision_due_at and now > req.decision_due_at:
            raise ConflictError(
                "The decision period for this request has expired; it can "
                "no longer be explicitly decided."
            )
        req.status = "approved" if approve else "rejected"
        req.decided_at = now
        req.decided_by_user_id = actor.user_id
        req.decision_note = note
        req.save(
            update_fields=[
                "status",
                "decided_at",
                "decided_by_user_id",
                "decision_note",
                "updated_at",
            ]
        )
        if approve:
            month_date = req.requested_date.replace(day=1)
            SpecialFoodCharge.objects.get_or_create(
                request=req.pk,
                student_user_id=req.user_id,
                month=month_date,
                defaults={"amount": Decimal("50.00")},
            )
        SpecialFoodTransition.objects.create(
            request=req.pk,
            from_status="requested",
            to_status=to_status,
            actor_user_id=actor.user_id,
            occurred_at=now,
            note=note,
        )
        topic = "special_food.decided"
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"special_food.decided:u{req.user_id}:{req.pk}",
            subject=("Special food request " + ("approved" if approve else "rejected")),
            body=(
                "Your special food request "
                + ("was approved" if approve else "was rejected")
                + (f". {note}" if note else "")
            ),
            recipient_user_id=req.user_id,
        )
    return req


def fulfill(actor, pk: int, to_status: str, note: str = "") -> SpecialFoodRequest:
    """BR-MMS-031: Caretaker records Served or Cancelled for an Approved
    request; fulfillment notification."""
    authz.require(actor, "mms.special_food.update")
    if to_status not in ("served", "cancelled"):
        raise ConflictError("Fulfillment status must be Served or Cancelled.")
    try:
        sm.resolve("approved", to_status, sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        req = (
            scoping.special_food_requests_for(actor)
            .filter(pk=pk, status="approved")
            .select_for_update()
            .first()
        )
        if req is None:
            raise NotFoundError("No Approved special food request with that id.")
        now = timezone.now()
        req.status = to_status
        req.decided_at = now
        req.decided_by_user_id = actor.user_id
        req.decision_note = note
        req.save(
            update_fields=[
                "status",
                "decided_at",
                "decided_by_user_id",
                "decision_note",
                "updated_at",
            ]
        )
        if to_status == "cancelled":
            SpecialFoodCharge.objects.filter(request=req.pk).delete()
        SpecialFoodTransition.objects.create(
            request=req.pk,
            from_status="approved",
            to_status=to_status,
            actor_user_id=actor.user_id,
            occurred_at=now,
            note=note,
        )
        notifications.enqueue(
            topic="special_food.fulfilled",
            dedupe_key=f"special_food.fulfilled:u{req.user_id}:{req.pk}",
            subject=f"Special food request {to_status}",
            body=f"Your special food request ({req.pk}) has been marked "
            f"as {to_status}." + (f" {note}" if note else ""),
            recipient_user_id=req.user_id,
        )
    return req


def default_reject_undecided() -> int:
    """UC-029 / BR-MMS-029: system auto-rejects Requested requests past the
    decision period. Idempotent."""
    now = timezone.now()
    due = SpecialFoodRequest.objects.filter(status="requested", decision_due_at__lte=now)
    count = 0
    for req in due:
        req.status = "rejected"
        req.decided_at = now
        req.decided_by_user_id = None  # system decision
        req.decision_note = "Default rejection: decision period expired."
        req.save(
            update_fields=[
                "status",
                "decided_at",
                "decided_by_user_id",
                "decision_note",
                "updated_at",
            ]
        )
        SpecialFoodTransition.objects.create(
            request=req.pk,
            from_status="requested",
            to_status="rejected_default",
            actor_user_id=None,
            occurred_at=now,
            note="Default rejection: decision period expired.",
        )
        notifications.enqueue(
            topic="special_food.default_rejected",
            dedupe_key=f"special_food.default_rejected:u{req.user_id}:{req.pk}",
            subject="Special food request rejected",
            body=f"Your special food request ({req.pk}) was not decided "
            f"within the decision period and has been rejected by "
            f"default.",
            recipient_user_id=req.user_id,
        )
        count += 1
    return count
