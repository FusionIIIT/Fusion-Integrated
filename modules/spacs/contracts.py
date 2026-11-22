"""SPACS public surface for other modules. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.spacs.models import AwardCandidate, ScholarshipApplication


@dataclass(frozen=True)
class ScholarshipAwardDTO:
    user_id: int
    application_number: str
    scheme_code: str
    scheme_name: str
    academic_cycle: str
    status: str
    is_renewal: bool


@dataclass(frozen=True)
class ConvocationAwardDTO:
    user_id: int
    scheme_code: str
    scheme_name: str
    convocation_year: int
    final_outcome: str


@dataclass(frozen=True)
class SpacsClearanceDTO:
    user_id: int
    cleared: bool
    active_scholarships_count: int
    message: str


def get_scholarship_awards(
    user_ids: Sequence[int],
    academic_cycle: str | None = None,
) -> dict[int, list[ScholarshipAwardDTO]]:
    """Returns approved scholarship awards for given users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = ScholarshipApplication.objects.filter(
        student_user_id__in=ids,
        status="approved",
    ).select_related("scheme")

    if academic_cycle:
        qs = qs.filter(academic_cycle=academic_cycle)

    results: dict[int, list[ScholarshipAwardDTO]] = {uid: [] for uid in ids}
    for app in qs:
        dto = ScholarshipAwardDTO(
            user_id=app.student_user_id,
            application_number=app.application_number,
            scheme_code=app.scheme.code,
            scheme_name=app.scheme.name,
            academic_cycle=app.academic_cycle,
            status=app.status,
            is_renewal=app.is_renewal,
        )
        results[app.student_user_id].append(dto)
    return results


def get_convocation_awards(
    user_ids: Sequence[int],
    convocation_year: int | None = None,
) -> dict[int, list[ConvocationAwardDTO]]:
    """Returns published convocation awards for given users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = AwardCandidate.objects.filter(
        student_user_id__in=ids,
        final_outcome="approved",
        award_cycle__status="published",
    ).select_related("award_cycle__scheme")

    if convocation_year:
        qs = qs.filter(award_cycle__convocation_year=convocation_year)

    results: dict[int, list[ConvocationAwardDTO]] = {uid: [] for uid in ids}
    for cand in qs:
        dto = ConvocationAwardDTO(
            user_id=cand.student_user_id,
            scheme_code=cand.award_cycle.scheme.code,
            scheme_name=cand.award_cycle.scheme.name,
            convocation_year=cand.award_cycle.convocation_year,
            final_outcome=cand.final_outcome,
        )
        results[cand.student_user_id].append(dto)
    return results


def get_spacs_clearances(
    user_ids: Sequence[int],
) -> dict[int, SpacsClearanceDTO]:
    """Returns scholarship/award clearance for students."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    out: dict[int, SpacsClearanceDTO] = {}
    for uid in ids:
        # SPACS does not hold dues that block graduation unless configured
        out[uid] = SpacsClearanceDTO(
            user_id=uid,
            cleared=True,
            active_scholarships_count=0,
            message="No pending SPACS obligations.",
        )
    return out
