"""Read helpers that are more than a scoped filter."""

from __future__ import annotations

from core.api.exceptions import ConflictError, NotFoundError
from modules.oap.domain import no_dues as nd
from modules.oap.domain import state_machines as sm
from modules.oap.domain.roles import AUTHORITY_DOMAIN
from modules.oap.models import BonafideRequest, NoDuesCase
from modules.oap.selectors import scoping


def bonafide_certificate_for(principal, pk: int) -> BonafideRequest:
    req = scoping.bonafide_for(principal).filter(pk=pk).first()
    if req is None:
        raise NotFoundError("Bonafide request not found.", code="not_found")
    if req.status != sm.BONAFIDE_APPROVED:
        raise ConflictError(
            "The certificate is available only after approval (OA-BR-22).",
            code="certificate_not_available",
        )
    return req


def no_dues_certificate_for(principal, pk: int) -> NoDuesCase:
    case = scoping.no_dues_for(principal).filter(pk=pk).first()
    if case is None:
        raise NotFoundError("No-dues case not found.", code="not_found")
    if not case.finalized:
        raise ConflictError(
            "The certificate is available only after finalization (OA-BR-34).",
            code="certificate_not_available",
        )
    return case


def no_dues_view_for(principal, case: NoDuesCase) -> dict:
    results = dict(case.results.values_list("domain", "result"))
    status = nd.derive_status(results, finalized=case.finalized)
    own = AUTHORITY_DOMAIN.get(principal.active_role)
    if own is not None:
        results = {own: results.get(own, nd.PENDING)}
    return {"status": status, "results": results}
