from collections.abc import Mapping, Sequence

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.models import (
    AuditEvent,
    AwardCandidate,
    AwardCycle,
    CatalogueVersion,
)


@transaction.atomic
def create_cycle(
    *,
    catalogue_version_id: int,
    candidate_source: str,
    actor_user_id: int,
) -> AwardCycle:
    version = (
        CatalogueVersion.objects.select_for_update()
        .select_related("entry")
        .filter(pk=catalogue_version_id, status="published")
        .first()
    )
    if version is None or version.entry.kind != "award":
        raise NotFoundError("No published award catalogue version was found.")
    if candidate_source not in {value for value, _ in AwardCycle.SOURCE_METHODS}:
        raise BadRequestError(
            "The candidate-source method is not supported.",
            code="unsupported_candidate_source",
        )
    cycle = AwardCycle.objects.create(
        catalogue_version=version,
        candidate_source=candidate_source,
        state="Award Cycle Open",
    )
    AuditEvent.objects.create(
        aggregate_type="award_cycle",
        aggregate_id=str(cycle.pk),
        event_type="award_cycle.created",
        actor_user_id=actor_user_id,
        actor_label="SPACS Convener",
        payload={
            "catalogue_version_id": version.pk,
            "candidate_source": candidate_source,
        },
    )
    return cycle


@transaction.atomic
def add_candidates(
    *,
    cycle_id: int,
    actor_user_id: int,
    candidates: Sequence[Mapping[str, object]],
) -> list[AwardCandidate]:
    cycle = AwardCycle.objects.select_for_update().filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("No such award cycle.")
    if cycle.state != "Award Cycle Open":
        raise ConflictError(
            "Candidates can only be added while the award cycle is open.",
            code="award_cycle_not_open",
        )
    if not candidates:
        raise BadRequestError(
            "At least one explicitly supplied candidate is required.",
            code="candidates_required",
        )
    rows = []
    seen_user_ids = set()
    for candidate in candidates:
        user_id = candidate.get("user_id")
        source_reference = candidate.get("source_reference", {})
        if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id < 1:
            raise BadRequestError(
                "Each candidate requires a positive user identifier.",
                code="invalid_candidate",
            )
        if not isinstance(source_reference, dict):
            raise BadRequestError(
                "Candidate source reference must be an object.",
                code="invalid_candidate",
            )
        if (
            user_id in seen_user_ids
            or AwardCandidate.objects.filter(
                cycle=cycle,
                user_id=user_id,
            ).exists()
        ):
            raise ConflictError(
                "A candidate can only appear once in an award cycle.",
                code="duplicate_award_candidate",
            )
        seen_user_ids.add(user_id)
        rows.append(
            AwardCandidate(
                cycle=cycle,
                user_id=user_id,
                source=cycle.candidate_source,
                source_reference=dict(source_reference),
                added_by_user_id=actor_user_id,
            )
        )
    saved = AwardCandidate.objects.bulk_create(rows)
    AuditEvent.objects.create(
        aggregate_type="award_cycle",
        aggregate_id=str(cycle.pk),
        event_type="award_cycle.candidates_added",
        actor_user_id=actor_user_id,
        actor_label="SPACS Convener",
        payload={
            "candidate_count": len(saved),
            "candidate_source": cycle.candidate_source,
        },
    )
    return saved
