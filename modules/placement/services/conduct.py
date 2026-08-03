"""Recording conduct incidents and applying the sanctions they point to.

Two steps on purpose. `record` writes what happened and returns what the
policy recommends; `apply_sanction` is the separate act of imposing it. Rule 19
says a student "may be debarred" and rule 21 leaves it to the Chairperson, so a
system that debarred on its own would be stricter than the signed policy.

The ladder is counted from the incidents on record rather than a stored tally,
which cannot drift out of step with them.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.placement.domain import conduct
from modules.placement.models import (
    ConductIncident,
    JobPosting,
    PlacementRegistration,
)
from modules.placement.services import notifications
from modules.placement.services.authz import require

log = logging.getLogger("fusion.placement.conduct")

P_DEBAR = "placement_cell.registration.debar"

VALID_KINDS = {k.value for k in conduct.IncidentKind}


def _registration(policy_season: str, user_id: int) -> PlacementRegistration:
    registration = PlacementRegistration.objects.filter(
        policy__season=policy_season, user_id=user_id).first()
    if registration is None:
        raise NotFoundError("That student is not registered for this season.")
    return registration


def prior_count(registration: PlacementRegistration, kind: str) -> int:
    """Unwaived incidents of this kind already on record."""
    return ConductIncident.objects.filter(
        registration=registration, kind=kind, waived=False).count()


@transaction.atomic
def record(*, season: str, user_id: int, kind: str, note: str, actor,
           posting_id: int | None = None) -> tuple[ConductIncident,
                                                   conduct.Recommendation]:
    """Log an incident and report the sanction the policy points to.

    Deliberately does not impose it. The caller sees the recommendation and
    decides, which is what rules 19 and 21 require.
    """
    require(actor, P_DEBAR)
    if kind not in VALID_KINDS:
        raise ConflictError(f"Unknown incident kind {kind!r}.", code="bad_kind")
    if not (note or "").strip():
        raise ConflictError("Say what happened — this is a disciplinary record.",
                            code="note_required")

    registration = _registration(season, user_id)
    posting = None
    if posting_id is not None:
        posting = JobPosting.objects.filter(pk=posting_id).first()
        if posting is None:
            raise NotFoundError("No such posting.")

    incident = ConductIncident.objects.create(
        registration=registration, user_id=user_id, kind=kind,
        posting=posting, note=note.strip()[:300],
        recorded_by_user_id=actor.user_id,
    )
    # Counted before this one, so the first incident recommends the first tier.
    recommendation = conduct.recommend(
        conduct.IncidentKind(kind),
        prior_incidents=prior_count(registration, kind) - 1)

    log.info("placement.conduct.recorded user=%s kind=%s rule=%s by=%s",
             user_id, kind, recommendation.rule, actor.user_id)
    return incident, recommendation


@transaction.atomic
def waive(*, incident_id: int, reason: str, actor) -> ConductIncident:
    """Rule 19's escape hatch — the student gave written notice in advance.

    The row stays and stops counting toward the ladder, so the history remains
    readable and the decision is attributable.
    """
    require(actor, P_DEBAR)
    if not (reason or "").strip():
        raise ConflictError("A waiver needs a reason.", code="reason_required")

    incident = ConductIncident.objects.select_for_update().filter(
        pk=incident_id).first()
    if incident is None:
        raise NotFoundError("No such incident.")
    if incident.waived:
        return incident

    incident.waived = True
    incident.waived_reason = reason.strip()[:300]
    incident.waived_by_user_id = actor.user_id
    incident.waived_at = timezone.now()
    incident.save(update_fields=["waived", "waived_reason", "waived_by_user_id",
                                 "waived_at", "updated_at"])
    log.info("placement.conduct.waived id=%s by=%s", incident_id, actor.user_id)
    return incident


@transaction.atomic
def apply_sanction(*, season: str, user_id: int, sanction: str, rule: str,
                   reason: str, actor) -> PlacementRegistration:
    """Impose a sanction. The human decision rules 19 and 21 call for."""
    require(actor, P_DEBAR)
    if sanction not in {s.value for s in conduct.Sanction}:
        raise ConflictError(f"Unknown sanction {sanction!r}.", code="bad_sanction")
    if not (reason or "").strip():
        raise ConflictError("A sanction needs a stated reason.",
                            code="reason_required")

    registration = PlacementRegistration.objects.select_for_update().filter(
        policy__season=season, user_id=user_id).first()
    if registration is None:
        raise NotFoundError("That student is not registered for this season.")

    chosen = conduct.Sanction(sanction)
    registration.sanction = chosen.value
    registration.sanction_rule = rule[:4]
    registration.sanctioned_at = timezone.now()
    registration.sanctioned_by_user_id = actor.user_id
    registration.debarred_reason = reason.strip()[:300]

    # Only a season-wide or permanent bar changes the registration's status.
    if chosen in (conduct.Sanction.BAR_SEASON, conduct.Sanction.BAR_PERMANENT):
        registration.status = "debarred"
    elif chosen is conduct.Sanction.DEREGISTER:
        registration.status = "opted_out"

    registration.save(update_fields=[
        "sanction", "sanction_rule", "sanctioned_at", "sanctioned_by_user_id",
        "debarred_reason", "status", "updated_at"])

    notifications.enqueue(
        topic="conduct.sanctioned",
        dedupe_key=f"conduct.sanctioned:{registration.pk}:"
                   f"{registration.sanctioned_at.isoformat()}",
        recipient_user_id=user_id,
        subject="A placement sanction has been recorded",
        body=(f"Rule {rule}: {reason}\n\nContact the Placement Cell if you "
              f"believe this is in error."),
        payload={"sanction": chosen.value, "rule": rule},
    )
    log.warning("placement.conduct.sanctioned user=%s sanction=%s rule=%s by=%s",
                user_id, chosen.value, rule, actor.user_id)
    return registration


@transaction.atomic
def lift(*, season: str, user_id: int, reason: str, actor) -> PlacementRegistration:
    """Reverse a sanction. Anything a human can impose, a human can undo."""
    require(actor, P_DEBAR)
    if not (reason or "").strip():
        raise ConflictError("Say why the sanction is being lifted.",
                            code="reason_required")

    registration = PlacementRegistration.objects.select_for_update().filter(
        policy__season=season, user_id=user_id).first()
    if registration is None:
        raise NotFoundError("That student is not registered for this season.")

    registration.sanction = ""
    registration.sanction_rule = ""
    registration.sanctioned_at = None
    registration.status = "registered"
    registration.debarred_reason = f"Lifted: {reason.strip()}"[:300]
    registration.save(update_fields=[
        "sanction", "sanction_rule", "sanctioned_at", "status",
        "debarred_reason", "updated_at"])
    log.info("placement.conduct.lifted user=%s by=%s", user_id, actor.user_id)
    return registration


def bars_posting(registration: PlacementRegistration,
                 posting: JobPosting) -> bool:
    """Whether the sanction in force blocks this particular drive.

    Rule 19's first tier is served by sitting out two drives, so it is counted
    against the postings published since the sanction rather than against a
    date — a quiet fortnight should not discharge it.
    """
    if not registration.sanction or registration.sanctioned_at is None:
        return False

    sanction = conduct.Sanction(registration.sanction)
    if sanction in (conduct.Sanction.BAR_SEASON, conduct.Sanction.BAR_PERMANENT):
        return True
    if sanction is not conduct.Sanction.BAR_NEXT_TWO:
        return False

    # "the NEXT two": a drive already open is not one, so this is never retroactive.
    if (posting.published_at is None
            or posting.published_at <= registration.sanctioned_at):
        return False

    drives_since = (JobPosting.objects
                    .filter(placement_year=registration.policy.season,
                            status__in=("published", "closed", "completed",
                                        "in_progress"),
                            published_at__gt=registration.sanctioned_at,
                            published_at__lt=posting.published_at)
                    .count())
    return conduct.bars_this_drive(sanction=sanction,
                                   drives_since_sanction=drives_since)
