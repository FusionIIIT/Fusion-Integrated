"""SPACS public surface. The ONLY thing other modules may import.

Enforces:
- ADR-0013 / Modular Monolith
- contracts_are_plural check: all get_* functions take a Sequence of IDs.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.spacs.models import ScholarshipApplication, CatalogueEntry, AwardCandidate


@dataclass(frozen=True)
class ApplicationDTO:
    application_id: int
    application_number: str
    user_id: int
    scheme_code: str
    scheme_title: str
    academic_cycle: str
    status: str
    is_renewal: bool


@dataclass(frozen=True)
class SchemeDTO:
    entry_id: int
    code: str
    title: str
    kind: str
    status: str


@dataclass(frozen=True)
class AwardWinnerDTO:
    candidate_id: int
    user_id: int
    award_title: str
    convocation_year: int


def get_applications(application_ids: Sequence[int]) -> dict[int, ApplicationDTO]:
    """Batched application lookup by primary key."""
    ids = {int(i) for i in application_ids if i is not None}
    if not ids:
        return {}

    qs = (
        ScholarshipApplication.objects.filter(pk__in=ids)
        .select_related("policy_version", "policy_version__catalogue_entry")
    )
    return {
        app.pk: ApplicationDTO(
            application_id=app.pk,
            application_number=app.application_number,
            user_id=app.user_id,
            scheme_code=app.policy_version.catalogue_entry.code,
            scheme_title=app.policy_version.catalogue_entry.title,
            academic_cycle=app.academic_cycle,
            status=app.status,
            is_renewal=app.is_renewal,
        )
        for app in qs
    }


def get_active_schemes(entry_ids: Sequence[int]) -> dict[int, SchemeDTO]:
    """Batched catalogue scheme lookup."""
    ids = {int(i) for i in entry_ids if i is not None}
    if not ids:
        return {}

    qs = CatalogueEntry.objects.filter(pk__in=ids)
    return {
        entry.pk: SchemeDTO(
            entry_id=entry.pk,
            code=entry.code,
            title=entry.title,
            kind=entry.kind,
            status=entry.status,
        )
        for entry in qs
    }


def get_student_awards(user_ids: Sequence[int]) -> dict[int, list[AwardWinnerDTO]]:
    """Batched lookup of official convocation awards won by students."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    winners = (
        AwardCandidate.objects.filter(
            user_id__in=ids,
            is_final_winner=True,
            award_cycle__status="published",
        )
        .select_related("award_cycle", "award_cycle__policy_version", "award_cycle__policy_version__catalogue_entry")
    )

    result: dict[int, list[AwardWinnerDTO]] = {uid: [] for uid in ids}
    for w in winners:
        result[w.user_id].append(
            AwardWinnerDTO(
                candidate_id=w.pk,
                user_id=w.user_id,
                award_title=w.award_cycle.policy_version.catalogue_entry.title,
                convocation_year=w.award_cycle.convocation_year,
            )
        )
    return result
