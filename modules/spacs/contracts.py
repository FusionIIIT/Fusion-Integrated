"""External contracts for SPACS module (ADR-0010, ADR-0013).

Other modules may import ONLY this file from modules.spacs.
All functions must be plural by signature and never mutate state.
"""

from typing import Sequence
from .models import SpacsApplication, SpacsAwardCandidate


def get_active_scholarships_for_students(user_ids: Sequence[int]) -> dict[int, list[dict]]:
    """Return approved active scholarships for given student user ids."""
    apps = SpacsApplication.objects.filter(
        applicant_user_id__in=user_ids,
        state__in=["approved", "renewed"],
    ).select_related("catalogue_entry")

    res = {uid: [] for uid in user_ids}
    for a in apps:
        res[a.applicant_user_id].append({
            "application_id": a.application_id,
            "scheme_code": a.catalogue_entry.scheme_code,
            "scheme_name": a.catalogue_entry.name,
            "academic_cycle": a.academic_cycle,
            "state": a.state,
        })
    return res


def get_convocation_awards_for_students(user_ids: Sequence[int]) -> dict[int, list[dict]]:
    """Return published convocation awards won by given student user ids."""
    candidates = SpacsAwardCandidate.objects.filter(
        student_user_id__in=user_ids,
        award_cycle__state="published",
        committee_recommendation="winner",
    ).select_related("award_cycle__catalogue_entry")

    res = {uid: [] for uid in user_ids}
    for c in candidates:
        res[c.student_user_id].append({
            "award_code": c.award_cycle.catalogue_entry.scheme_code,
            "award_name": c.award_cycle.catalogue_entry.name,
            "academic_cycle": c.award_cycle.academic_cycle,
        })
    return res
