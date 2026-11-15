"""Maintain and publish policy and calendar versions (EL-UC-014, EL-UC-015)."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm import registry
from modules.elm.domain import permissions as p
from modules.elm.domain import policy as policy_domain
from modules.elm.domain import routing
from modules.elm.models import CalendarEntry, CalendarVersion, PolicyVersion
from modules.elm.models.config import DRAFT, PUBLISHED
from modules.elm.services.authz import require


def _approvers() -> set[str]:
    return {d for d, codes in registry.ROLE_GRANTS.items()
            if p.P_REVIEW in codes or p.P_APPROVE in codes}


def validate_policy(params: dict, hierarchy: dict) -> None:
    try:
        policy_domain.parse(params)
        routing.parse_hierarchy(hierarchy)
    except (policy_domain.PolicyInvalid, routing.HierarchyInvalid) as exc:
        raise BadRequestError(str(exc), code="invalid_policy") from exc
    unknown = routing.roles_in(hierarchy) - _approvers()
    if unknown:
        raise BadRequestError(
            "These designations are named in the hierarchy but hold no ELM decision "
            f"permission: {', '.join(sorted(unknown))}.", code="invalid_policy")


def create_policy(actor, *, name: str, params: dict, hierarchy: dict,
                  effective_from: date) -> PolicyVersion:
    require(actor, p.P_POLICY)
    validate_policy(params, hierarchy)
    return PolicyVersion.objects.create(
        name=name, params=params, hierarchy=hierarchy, effective_from=effective_from,
        created_by_user_id=getattr(actor, "user_id", None))


def update_policy(actor, pk: int, **fields) -> PolicyVersion:
    require(actor, p.P_POLICY)
    with transaction.atomic():
        pv = PolicyVersion.objects.select_for_update().filter(pk=pk).first()
        if pv is None:
            raise NotFoundError("No such policy version.")
        if pv.status != DRAFT:
            raise ConflictError("A published policy cannot be edited; create a new version.",
                                code="policy_published")
        for k, v in fields.items():
            if v is not None:
                setattr(pv, k, v)
        validate_policy(pv.params, pv.hierarchy)
        pv.save()
        return pv


def publish_policy(actor, pk: int) -> PolicyVersion:
    require(actor, p.P_POLICY)
    with transaction.atomic():
        pv = PolicyVersion.objects.select_for_update().filter(pk=pk).first()
        if pv is None:
            raise NotFoundError("No such policy version.")
        if pv.status == PUBLISHED:
            raise ConflictError("This policy version is already published.",
                                code="policy_published")
        validate_policy(pv.params, pv.hierarchy)
        pv.status, pv.published_at = PUBLISHED, timezone.now()
        pv.save()
        return pv


def create_calendar(actor, *, name: str, effective_from: date,
                    entries: list[dict]) -> CalendarVersion:
    require(actor, p.P_CALENDAR)
    with transaction.atomic():
        cv = CalendarVersion.objects.create(
            name=name, effective_from=effective_from,
            created_by_user_id=getattr(actor, "user_id", None))
        _replace_entries(cv, entries)
        return cv


def update_calendar(actor, pk: int, *, name=None, effective_from=None,
                    entries=None) -> CalendarVersion:
    require(actor, p.P_CALENDAR)
    with transaction.atomic():
        cv = CalendarVersion.objects.select_for_update().filter(pk=pk).first()
        if cv is None:
            raise NotFoundError("No such calendar version.")
        if cv.status != DRAFT:
            raise ConflictError("A published calendar cannot be edited; create a new version.",
                                code="calendar_published")
        if name is not None:
            cv.name = name
        if effective_from is not None:
            cv.effective_from = effective_from
        cv.save()
        if entries is not None:
            _replace_entries(cv, entries)
        return cv


def _replace_entries(cv: CalendarVersion, entries: list[dict]) -> None:
    cv.entries.all().delete()
    for e in entries:
        if e["end_date"] < e["start_date"]:
            raise BadRequestError(f"{e['name']}: the end date is before the start date.",
                                  code="invalid_calendar")
        CalendarEntry.objects.create(version=cv, **e)


def publish_calendar(actor, pk: int) -> CalendarVersion:
    require(actor, p.P_CALENDAR)
    with transaction.atomic():
        cv = CalendarVersion.objects.select_for_update().filter(pk=pk).first()
        if cv is None:
            raise NotFoundError("No such calendar version.")
        if cv.status == PUBLISHED:
            raise ConflictError("This calendar version is already published.",
                                code="calendar_published")
        cv.status, cv.published_at = PUBLISHED, timezone.now()
        cv.save()
        return cv
