"""PHC's read-only public surface. Every getter is plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.phc.domain.policy import CLAIM_KIND_MESSAGE, is_reimbursable_kind
from modules.phc.models import Patient


@dataclass(frozen=True)
class PHCProfileDTO:
    user_id: int
    has_patient_record: bool
    may_claim_reimbursement: bool
    message: str


def get_phc_profiles(user_ids: Sequence[int]) -> dict[int, PHCProfileDTO]:
    """Return one profile per id, including ids with no PHC record."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}
    found = {p.user_id: p for p in Patient.objects.filter(user_id__in=ids)}
    return {
        uid: PHCProfileDTO(
            user_id=uid,
            has_patient_record=uid in found,
            may_claim_reimbursement=(uid in found and is_reimbursable_kind(
                found[uid].kind)),
            message=("Eligible for reimbursement" if uid in found
                     and is_reimbursable_kind(found[uid].kind)
                     else CLAIM_KIND_MESSAGE),
        )
        for uid in ids
    }
