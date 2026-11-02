"""Automatic check-out and pass-expiry sweeps (VMS-CFR-023, CFR-024; UC-038;
BR-101, BR-105, BR-190; decision D-11).

Both sweeps are idempotent, run one transaction per row and never let one bad
row stop the rest. The actor is the system (``actor=None`` -> audit role
"system", permission ``vms.visit.auto_checkout``).

Extension-aware: an approved extension moves ``VisitPass.valid_until``
(`services.extensions`), so reading that column is reading the latest end.
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.vms.models import VisitPass
from modules.vms.selectors import roster
from modules.vms.services import checkout
from modules.vms.services.common import audit

log = logging.getLogger("fusion.vms.autocheckout")


def sweep(now: datetime | None = None) -> int:
    """Check out every visitor still on site past their pass end (BR-101). Returns the count."""
    now = now or timezone.now()
    ids = list(roster.on_site().filter(valid_until__lte=now).values_list("pk", flat=True))
    done = 0
    for pk in ids:
        try:
            if checkout.complete_visit(pk, "auto", actor=None) is not None:
                done += 1
        except Exception:
            log.exception("vms.autocheckout.failed pass=%s", pk)
    return done


def expire_unused_passes(now: datetime | None = None) -> int:
    """Deactivate passes past their end whose visitor is not on site (BR-190).

    A pass with an open check-in is left to `sweep`, which checks the visitor out
    first. The request status is left alone: the request state table has no
    ``approved -> expired`` move.
    """
    now = now or timezone.now()
    ids = list(VisitPass.objects.filter(is_active=True, valid_until__lte=now)
               .values_list("pk", flat=True))
    expired = 0
    for pk in ids:
        try:
            with transaction.atomic():
                vp = VisitPass.objects.select_for_update().get(pk=pk)
                if (not vp.is_active or vp.valid_until > now
                        or roster.open_check_in(vp) is not None):
                    continue
                vp.is_active = False
                vp.save(update_fields=["is_active"])
                audit.record(actor=None, action="vms.pass.expired", entity=vp, detail={
                    "valid_until": vp.valid_until.isoformat(),
                    "request_id": vp.visit_request_id})
                expired += 1
        except Exception:
            log.exception("vms.autocheckout.expire_failed pass=%s", pk)
    return expired
