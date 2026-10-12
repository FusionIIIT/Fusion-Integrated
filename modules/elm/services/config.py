"""Policy and calendar configuration services (EL-UC-014, EL-UC-015)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.elm.domain.policy import PolicyInvalid, parse
from modules.elm.domain.routing import HierarchyInvalid, parse_hierarchy
from modules.elm.models import CalendarEntry, CalendarVersion, PolicyVersion
from modules.elm.models.config import PUBLISHED


def validate_policy(params: dict, hierarchy: dict) -> None:
    try:
        parse(params)
        parse_hierarchy(hierarchy)
    except (PolicyInvalid, HierarchyInvalid) as exc:
        raise BadRequestError(str(exc), code="invalid_policy") from exc


@transaction.atomic
def create_policy(*, name: str, effective_from, params: dict, hierarchy: dict,
                  actor_user_id: int | None = None) -> PolicyVersion:
    validate_policy(params, hierarchy)
    return PolicyVersion.objects.create(
        name=name,
        effective_from=effective_from,
        params=params,
        hierarchy=hierarchy,
        created_by_user_id=actor_user_id,
    )


@transaction.atomic
def publish_policy(pk: int) -> PolicyVersion:
    pv = PolicyVersion.objects.select_for_update().get(pk=pk)
    if pv.status == PUBLISHED:
        raise ConflictError("Policy version is already published.", code="already_published")
    validate_policy(pv.params, pv.hierarchy)
    pv.status = PUBLISHED
    pv.published_at = timezone.now()
    pv.save(update_fields=["status", "published_at", "updated_at"])
    return pv


@transaction.atomic
def create_calendar(*, name: str, effective_from, entries: list[dict],
                    actor_user_id: int | None = None) -> CalendarVersion:
    cv = CalendarVersion.objects.create(
        name=name,
        effective_from=effective_from,
        created_by_user_id=actor_user_id,
    )
    for e in entries:
        if e["end_date"] < e["start_date"]:
            raise BadRequestError("Calendar entry cannot end before it starts.",
                                  code="invalid_calendar")
        CalendarEntry.objects.create(version=cv, **e)
    return cv


@transaction.atomic
def publish_calendar(pk: int) -> CalendarVersion:
    cv = CalendarVersion.objects.select_for_update().get(pk=pk)
    if cv.status == PUBLISHED:
        raise ConflictError("Calendar version is already published.", code="already_published")
    cv.status = PUBLISHED
    cv.published_at = timezone.now()
    cv.save(update_fields=["status", "published_at", "updated_at"])
    return cv
