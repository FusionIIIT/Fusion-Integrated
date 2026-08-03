"""Registering for a season (rules 1, 20, 21).

Nothing created a PlacementRegistration before this, which meant `can_apply`
refused everyone with `not_registered` — the whole application flow was closed
in production.

A student registers themselves. The two routes that need money — rule 20's
late fee and rule 21's re-registration — are staff actions, because both
require the office to have seen a challan and, for rule 21, the Chairperson's
approval. PCMS records the reference; it never takes payment.
"""
from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.placement.domain import conduct
from modules.placement.domain import registration as rules
from modules.placement.models import PlacementPolicy, PlacementRegistration
from modules.placement.services import facts as facts_service
from modules.placement.services import notifications
from modules.placement.services.authz import require

log = logging.getLogger("fusion.placement.registration")

P_MANAGE = "placement_cell.registration.manage"


def _policy(season: str) -> PlacementPolicy:
    policy = PlacementPolicy.objects.filter(season=season).first()
    if policy is None:
        raise ConflictError(f"No placement policy is configured for {season}.",
                            code="policy_missing")
    return policy


def _season_terms(policy: PlacementPolicy) -> rules.SeasonTerms:
    return rules.SeasonTerms(
        is_active=policy.is_active,
        closes_on=policy.registration_closes_on,
        min_cpi=policy.min_cpi_to_register,
        allow_backlogs=policy.allow_backlog_registration,
        late_fee=policy.late_registration_fee,
        reregistration_fee=policy.reregistration_fee,
    )


def _applicant(policy: PlacementPolicy, user_id: int) -> rules.Applicant:
    """Academic facts come from the IAM projection, never from the student."""
    existing = PlacementRegistration.objects.filter(
        policy=policy, user_id=user_id).first()
    f = facts_service.gather([user_id], policy=policy).get(user_id, {})

    return rules.Applicant(
        cpi=f.get("cpi"),
        active_backlogs=f.get("active_backlogs"),
        current_status=existing.status if existing else None,
        reregistration_count=existing.reregistration_count if existing else 0,
        is_permanently_barred=bool(
            existing and existing.sanction == conduct.Sanction.BAR_PERMANENT),
    )


def assess(*, season: str, user_id: int) -> rules.Terms:
    """What route is open to this student. Read-only; safe to call from a GET."""
    policy = _policy(season)
    return rules.assess(_season_terms(policy), _applicant(policy, user_id),
                        today=timezone.localdate())


@transaction.atomic
def register(*, season: str, user_id: int) -> PlacementRegistration:
    """Rule 1. A student opting themselves into the season."""
    policy = _policy(season)
    terms = rules.assess(_season_terms(policy), _applicant(policy, user_id),
                         today=timezone.localdate())

    if terms.route is not rules.Route.OPEN:
        # LATE and REREGISTER are real routes, but both go through the office.
        raise ConflictError(terms.message, code=terms.reason)

    try:
        registration = PlacementRegistration.objects.create(
            policy=policy, user_id=user_id, status="registered",
            registered_at=timezone.now())
    except IntegrityError as exc:
        # Two tabs. The unique constraint decides; the loser reads the winner.
        existing = PlacementRegistration.objects.filter(
            policy=policy, user_id=user_id).first()
        if existing is None:
            raise
        raise ConflictError("You are already registered.",
                            code="already_registered") from exc

    _notify(registration, "You are registered for placement",
            f"You are registered for the {season} placement season.")
    log.info("placement.registration.created user=%s season=%s", user_id, season)
    return registration


@transaction.atomic
def approve_late(*, season: str, user_id: int, fee_reference: str,
                 actor) -> PlacementRegistration:
    """Rule 20 — registering after the deadline, on the late fee."""
    require(actor, P_MANAGE)
    if not (fee_reference or "").strip():
        raise ConflictError(
            "Record the challan or receipt number the student produced.",
            code="fee_reference_required")

    policy = _policy(season)
    terms = rules.assess(_season_terms(policy), _applicant(policy, user_id),
                         today=timezone.localdate())
    if terms.route not in (rules.Route.LATE, rules.Route.OPEN):
        raise ConflictError(terms.message, code=terms.reason)

    registration, _ = PlacementRegistration.objects.get_or_create(
        policy=policy, user_id=user_id,
        defaults={"status": "registered", "registered_at": timezone.now()})
    registration.status = "registered"
    registration.registered_late = True
    registration.late_fee_reference = fee_reference.strip()[:80]
    registration.approved_by_user_id = actor.user_id
    registration.registered_at = registration.registered_at or timezone.now()
    registration.save(update_fields=[
        "status", "registered_late", "late_fee_reference",
        "approved_by_user_id", "registered_at", "updated_at"])

    _notify(registration, "Your late registration is approved",
            f"You are registered for the {season} placement season.")
    log.info("placement.registration.late_approved user=%s by=%s",
             user_id, actor.user_id)
    return registration


@transaction.atomic
def reregister(*, season: str, user_id: int, fee_reference: str,
               actor) -> PlacementRegistration:
    """Rule 21 — the one way back after de-registration."""
    require(actor, P_MANAGE)
    if not (fee_reference or "").strip():
        raise ConflictError(
            "Record the challan or receipt number the student produced.",
            code="fee_reference_required")

    policy = _policy(season)
    registration = PlacementRegistration.objects.select_for_update().filter(
        policy=policy, user_id=user_id).first()
    if registration is None:
        raise NotFoundError("That student has no registration for this season.")

    terms = rules.assess(_season_terms(policy), _applicant(policy, user_id),
                         today=timezone.localdate())
    if terms.route is not rules.Route.REREGISTER:
        raise ConflictError(terms.message, code=terms.reason)

    registration.status = "registered"
    # The counter is what closes the route: rule 21 allows this exactly once.
    registration.reregistration_count += 1
    registration.reregistration_reference = fee_reference.strip()[:80]
    registration.approved_by_user_id = actor.user_id
    registration.sanction = ""
    registration.sanction_rule = ""
    registration.sanctioned_at = None
    registration.save(update_fields=[
        "status", "reregistration_count", "reregistration_reference",
        "approved_by_user_id", "sanction", "sanction_rule", "sanctioned_at",
        "updated_at"])

    _notify(registration, "Your re-registration is approved",
            f"You are registered again for the {season} placement season. "
            f"Rule 21 allows this once only.")
    log.info("placement.registration.rereg user=%s by=%s count=%d",
             user_id, actor.user_id, registration.reregistration_count)
    return registration


@transaction.atomic
def opt_out(*, season: str, user_id: int, reason: str = "") -> PlacementRegistration:
    """A student withdrawing from the season.

    Note the asymmetry with rule 21: coming back costs the re-registration fee
    and is available once, so the caller should say so before confirming.
    """
    policy = _policy(season)
    registration = PlacementRegistration.objects.select_for_update().filter(
        policy=policy, user_id=user_id).first()
    if registration is None:
        raise NotFoundError("You are not registered for this season.")
    if registration.status == "debarred":
        raise ConflictError("A debarment is in force; you cannot opt out of it.",
                            code="debarred")

    registration.status = "opted_out"
    registration.debarred_reason = reason.strip()[:300]
    registration.save(update_fields=["status", "debarred_reason", "updated_at"])
    log.info("placement.registration.opted_out user=%s", user_id)
    return registration


def _notify(registration: PlacementRegistration, subject: str, body: str) -> None:
    notifications.enqueue(
        topic="registration.confirmed",
        dedupe_key=f"registration.confirmed:{registration.pk}:"
                   f"{registration.status}:{registration.reregistration_count}",
        recipient_user_id=registration.user_id,
        subject=subject, body=body,
        payload={"season": registration.policy.season,
                 "status": registration.status})
