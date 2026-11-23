"""Inventors, ownership shares and agreements (UC-PMS-003; BR-PMS-073..078)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Inventor
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import lock, now, owner_only, require, ruled

P_UPDATE = "pms.inventor.update"


def _parse(rows) -> list[validation.InventorInput]:
    if not isinstance(rows, list):
        raise InvalidInput("Send the inventors as a list.", code="inventors_required")
    ids = [r.get("user_id") for r in rows if isinstance(r, dict) and r.get("user_id")]
    known = directory.get_users(ids) if ids else {}
    out = []
    for r in rows:
        if not isinstance(r, dict):
            raise InvalidInput("Each inventor needs a name and a share.",
                               code="inventor_name_required")
        uid = r.get("user_id")
        if uid is not None:
            if uid not in known:
                raise InvalidInput("One of the institute inventors is not in the directory; "
                                   "pick them again from the search.", code="unknown_person")
            name = known[uid].display_name
        else:
            name = (r.get("name") or "").strip()
        out.append(validation.InventorInput(
            name=name, share_percent=validation.parse_share(r.get("share_percent")),
            user_id=uid, email=(r.get("email") or "").strip(),
            affiliation=(r.get("affiliation") or "").strip()))
    validation.check_inventors(out)
    return out


def _key(user_id, name: str, affiliation: str):
    return ("u", user_id) if user_id is not None else ("x", name.lower(), affiliation.lower())


@ruled
def replace_inventors(*, actor, pk: int, inventors) -> list[Inventor]:
    """Replace the whole set at once, so the 100% total is checked on what will be stored."""
    require(actor, P_UPDATE)
    parsed = _parse(inventors)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        if app.status not in sm.APPLICANT_EDITABLE:
            raise ConflictError("Inventors can be changed only while the application is a "
                                "draft or being revised.", code="not_editable")
        existing = {_key(i.user_id, i.name, i.affiliation): i for i in app.inventors.all()}
        kept, affected = set(), set()
        for inv in parsed:
            key = _key(inv.user_id, inv.name, inv.affiliation)
            row = existing.get(key)
            if row is None:
                row = Inventor(application=app)
            elif row.share_percent != inv.share_percent:
                # Blueprint Q-9: a changed share needs a fresh agreement and consent.
                row.agreement_completed_at = row.consent_recorded_at = None
                row.agreement_reference = ""
            row.user_id, row.name, row.email = inv.user_id, inv.name, inv.email
            row.affiliation, row.share_percent = inv.affiliation, inv.share_percent
            row.save()
            kept.add(row.pk)
            if inv.user_id:
                affected.add(inv.user_id)
        for gone in [i for i in existing.values() if i.pk not in kept]:
            if gone.user_id:
                affected.add(gone.user_id)
            gone.delete()
        entry = audit.record(actor, "inventors.replaced", application=app, obj=app,
                             details={"count": len(parsed)})
        notifications.enqueue_many(
            topic="inventors.changed", key=f"inventors:{entry.pk}",
            recipients=sorted(affected - {actor.user_id}),
            subject="Inventor information changed",
            body="The inventors or ownership shares on a patent application that names you "
                 "were changed. Open Patent Management to review them.")
        return list(app.inventors.order_by("id"))


@ruled
def record_agreement(*, actor, pk: int, inventor_id: int, agreement_reference: str,
                     consent: bool) -> Inventor:
    """BR-PMS-075 / 078: recorded by the applicant; e-signatures stay off (BR-PMS-076, 077)."""
    require(actor, P_UPDATE)
    ref = (agreement_reference or "").strip()
    if not ref or len(ref) > 200:
        raise InvalidInput("Give the agreement's reference, such as its file number "
                           "(at most 200 characters).", code="agreement_reference_required")
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        if app.status in sm.TERMINAL or app.status in sm.POST_FILING:
            raise ConflictError("Agreements are recorded before filing.", code="not_editable")
        inv = app.inventors.select_for_update().filter(pk=inventor_id).first()
        if inv is None:
            raise NotFoundError("No such inventor on this application.", code="not_found")
        inv.agreement_reference = ref
        inv.agreement_completed_at = inv.agreement_completed_at or now()
        if consent:
            inv.consent_recorded_at = inv.consent_recorded_at or now()
        inv.save(update_fields=["agreement_reference", "agreement_completed_at",
                                "consent_recorded_at", "updated_at"])
        audit.record(actor, "inventor.agreement_recorded", application=app, obj=inv,
                     details={"consent": bool(consent)})
    return inv
