"""Patient lookup for PHC Staff (AFR-PHC-006), asked of the IAM so students are found too."""
from __future__ import annotations

from fusion_auth.client import get_client

PATIENT_KINDS = frozenset({"student", "faculty", "staff"})
MIN_QUERY = 2


def search_patients(q: str, limit: int = 25):
    return [u for u in get_client().search_users(q=q.strip(), limit=limit)
            if u.kind in PATIENT_KINDS]
