"""Pass issuance (VMS-BR-190, BR-193). Termination is lane D's (services/termination.py)."""
from __future__ import annotations

import secrets

from django.db import connection, transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.vms.domain import policy_eval
from modules.vms.models import VisitPass, VisitRequest
from modules.vms.services import policy
from modules.vms.services.common import audit

_OTP_LOCK_KEY = 0x564D534F  # "VMSO": serialises OTP allocation on Postgres


def _unique_otp() -> str:
    """6 digits, unique among active passes. The column is not unique in the
    schema, so allocation is serialised with an advisory lock on Postgres."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", [_OTP_LOCK_KEY])
    for _ in range(50):
        otp = f"{secrets.randbelow(10**6):06d}"
        if not VisitPass.objects.filter(otp=otp, is_active=True).exists():
            return otp
    raise ConflictError("No free OTP available.", code="otp_exhausted")


def issue_pass(*, request, pass_type, issued_by, valid_from=None, valid_until=None,
               zones=None) -> VisitPass:
    """Issue the pass for an APPROVED request.

    Validity is the request window (or the explicit one), capped by the
    max-visit hours of the policy that applied when the request was made
    (BR-190/193); walk-in passes are also capped by walk_in_pass_hours.
    `issued_by` is a Principal or a user id. `zones` defaults to the requested
    zones.
    """
    pass_type = getattr(pass_type, "value", pass_type)
    if pass_type not in VisitPass.PassType.values:                 # BR-211
        raise BadRequestError("Unknown pass type.", code="invalid_pass_type")
    issuer_id = issued_by if isinstance(issued_by, int) else issued_by.user_id
    with transaction.atomic():
        vr = VisitRequest.objects.select_for_update().get(pk=request.pk)
        if vr.status != VisitRequest.Status.APPROVED:
            raise ConflictError("A pass can only be issued for an approved request.",
                                code="request_not_approved")
        if vr.passes.filter(is_active=True).exists():
            raise ConflictError("This request already has an active pass.",
                                code="pass_already_issued")
        snap = policy.snapshot_for(vr)
        start = valid_from or vr.scheduled_start
        end = valid_until or vr.scheduled_end
        limit = snap.max_visit_hours
        if pass_type == VisitPass.PassType.WALK_IN:
            limit = min(limit, snap.walk_in_pass_hours)
        end = policy_eval.capped_end(start, end, limit)
        vp = VisitPass.objects.create(
            visit_request=vr, pass_type=pass_type,
            qr_token=secrets.token_urlsafe(32), otp=_unique_otp(),
            valid_from=start, valid_until=end, issued_by_user_id=issuer_id,
            issued_for_source=vr.source, event_id=vr.event_id)
        vp.allowed_zones.set(list(zones) if zones is not None else vr.requested_zones.all())
        audit.record(actor=issued_by, action="vms.pass.issued", entity=vp, detail={
            "request_id": vr.pk, "pass_type": pass_type,
            "valid_from": start.isoformat(), "valid_until": end.isoformat(),
            "policy_version": snap.version})
    return vp


def terminate_pass(*, actor, pass_id, reason):
    """Early termination (VMS-CFR-024, BR-073); delegates to lane D's service."""
    from modules.vms.services import termination
    return termination.terminate(actor=actor, pass_id=pass_id, reason=reason)
