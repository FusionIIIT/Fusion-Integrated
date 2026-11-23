"""Licensing and technology-transfer requests: kinds and routing (BR-PMS-088)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.pms.domain.errors import InvalidInput
from modules.pms.domain.policy import LicensingRoute

KINDS = ("licensing", "technology_transfer")         # PMS-AFR-158, 159
NOT_SHARED = "not_shared_no_integration"            # BR-PMS-139 / PMS-AFR-163


@dataclass(frozen=True)
class Target:
    kind: str
    director_user_id: int | None
    committee_name: str


def route_target(route: LicensingRoute | None) -> Target | None:
    """None when nothing is configured: the request waits, and no committee is invented."""
    if route is None:
        return None
    return Target(route.kind, route.director_user_id, route.committee_name)


def check_request(kind: str, summary) -> str:
    if kind not in KINDS:
        raise InvalidInput("Choose Licensing or Technology transfer.", code="invalid_kind")
    text = (summary or "").strip()
    if not text:
        raise InvalidInput("Describe what you want to license or transfer.",
                           code="summary_required")
    return text[:5000]
