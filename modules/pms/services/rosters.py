"""Director and attorney-panel rosters, effective-dated (UC-PMS-026; ruling C13; PMS-AFR-030)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import DirectorProfile, PanelAttorney
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import audit
from modules.pms.services.base import now, require, ruled

P_DIRECTORS = "pms.director_profile.update"
P_PANEL = "pms.attorney_panel.update"


def _check(user_id, domain_codes) -> list[str]:
    if not isinstance(user_id, int) or not directory.get_users([user_id]).get(user_id):
        raise InvalidInput("Pick the person from the directory search.", code="unknown_person")
    if not isinstance(domain_codes, list) or not domain_codes:
        raise InvalidInput("Choose at least one technical area.", code="areas_required")
    offered = policy_selector.current().domain_codes
    unknown = sorted(set(domain_codes) - offered)
    if unknown:
        raise InvalidInput("These areas are not configured: " + ", ".join(unknown) + ".",
                           code="unknown_area")
    return sorted(set(domain_codes))


def _set(model, perm: str, *, actor, user_id, domain_codes):
    require(actor, perm)
    areas = _check(user_id, domain_codes)
    stamp = now()
    try:
        with transaction.atomic():
            current = model.objects.select_for_update().filter(user_id=user_id,
                                                                valid_to__isnull=True).first()
            if current is not None:
                current.valid_to, current.ended_by_user_id = stamp, actor.user_id
                current.save(update_fields=["valid_to", "ended_by_user_id", "updated_at"])
            row = model.objects.create(user_id=user_id, domain_codes=areas, valid_from=stamp,
                                       added_by_user_id=actor.user_id)
            audit.record(actor, f"{model.__name__.lower()}.set", obj=row,
                         details={"user_id": user_id, "areas": areas,
                                  "replaces": getattr(current, "pk", None)})
    except IntegrityError as exc:
        raise ConflictError("Someone changed this roster entry at the same moment; refresh and "
                            "try again.", code="roster_conflict") from exc
    return row


def _end(model, perm: str, *, actor, entry_id: int):
    require(actor, perm)
    with transaction.atomic():
        row = model.objects.select_for_update().filter(pk=entry_id).first()
        if row is None:
            raise NotFoundError("No such roster entry.", code="not_found")
        if row.valid_to is not None:
            raise ConflictError("This person has already left the roster.", code="already_ended")
        row.valid_to, row.ended_by_user_id = now(), actor.user_id
        row.save(update_fields=["valid_to", "ended_by_user_id", "updated_at"])
        audit.record(actor, f"{model.__name__.lower()}.ended", obj=row,
                     details={"user_id": row.user_id})
    return row


@ruled
def set_director(*, actor, user_id, domain_codes) -> DirectorProfile:
    """Adding someone already listed ends their old row and starts a new one (Step 2.8)."""
    return _set(DirectorProfile, P_DIRECTORS, actor=actor, user_id=user_id,
                domain_codes=domain_codes)


@ruled
def end_director(*, actor, entry_id: int) -> DirectorProfile:
    return _end(DirectorProfile, P_DIRECTORS, actor=actor, entry_id=entry_id)


@ruled
def set_panel_attorney(*, actor, user_id, domain_codes) -> PanelAttorney:
    return _set(PanelAttorney, P_PANEL, actor=actor, user_id=user_id,
                domain_codes=domain_codes)


@ruled
def end_panel_attorney(*, actor, entry_id: int) -> PanelAttorney:
    return _end(PanelAttorney, P_PANEL, actor=actor, entry_id=entry_id)
