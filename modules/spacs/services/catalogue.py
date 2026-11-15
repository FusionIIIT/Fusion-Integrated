from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.models import AuditEvent, CatalogueEntry, CatalogueVersion

_VERSION_FIELDS = {
    "configuration",
    "approval_reference",
    "effective_from",
    "effective_to",
    "application_opens_at",
    "application_closes_at",
    "renewal_opens_at",
    "renewal_closes_at",
}


def _audit(
    *,
    version: CatalogueVersion,
    actor_user_id: int,
    event_type: str,
    payload: dict,
) -> None:
    AuditEvent.objects.create(
        aggregate_type="catalogue_version",
        aggregate_id=str(version.pk),
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_label="SPACS Convener",
        payload=payload,
    )


def _audit_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _audit_values(values: Mapping[str, object]) -> dict[str, object]:
    return {key: _audit_value(value) for key, value in values.items()}


def _date_values_are_ordered(values: Mapping[str, object]) -> bool:
    effective_from = values.get("effective_from")
    effective_to = values.get("effective_to")
    opens_at = values.get("application_opens_at")
    closes_at = values.get("application_closes_at")
    renewal_opens_at = values.get("renewal_opens_at")
    renewal_closes_at = values.get("renewal_closes_at")
    return not (
        (effective_from is not None and effective_to is not None and effective_to < effective_from)
        or (opens_at is not None and closes_at is not None and closes_at < opens_at)
        or (
            renewal_opens_at is not None
            and renewal_closes_at is not None
            and renewal_closes_at < renewal_opens_at
        )
    )


@transaction.atomic
def create_draft(
    *,
    kind: str,
    configuration: dict,
    actor_user_id: int,
) -> tuple[CatalogueEntry, CatalogueVersion]:
    if kind not in dict(CatalogueEntry.KIND):
        raise BadRequestError("kind must be scholarship or award.", code="invalid_catalogue_kind")
    if not isinstance(configuration, dict):
        raise BadRequestError("configuration must be a JSON object.", code="invalid_configuration")

    entry = CatalogueEntry.objects.create(kind=kind)
    version = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        configuration=configuration,
    )
    _audit(
        version=version,
        actor_user_id=actor_user_id,
        event_type="catalogue.version_created",
        payload={"status": version.status, "configuration": configuration},
    )
    return entry, version


@transaction.atomic
def create_version(
    *,
    entry_id: int,
    configuration: dict,
    actor_user_id: int,
) -> CatalogueVersion:
    if not isinstance(configuration, dict):
        raise BadRequestError("configuration must be a JSON object.", code="invalid_configuration")
    entry = CatalogueEntry.objects.select_for_update().filter(pk=entry_id).first()
    if entry is None:
        raise NotFoundError("No such catalogue entry.")

    latest = entry.versions.order_by("-version_number").first()
    version_number = 1 if latest is None else latest.version_number + 1
    version = CatalogueVersion.objects.create(
        entry=entry,
        version_number=version_number,
        configuration=configuration,
    )
    _audit(
        version=version,
        actor_user_id=actor_user_id,
        event_type="catalogue.version_created",
        payload={"status": version.status, "configuration": configuration},
    )
    return version


@transaction.atomic
def update_version(
    *,
    version_id: int,
    changes: Mapping[str, object],
    actor_user_id: int,
) -> CatalogueVersion:
    if not changes:
        raise BadRequestError("At least one version field is required.", code="empty_update")
    unknown = set(changes) - _VERSION_FIELDS
    if unknown:
        raise BadRequestError(
            f"Unsupported version fields: {', '.join(sorted(unknown))}.",
            code="unsupported_version_fields",
        )

    version = CatalogueVersion.objects.select_for_update().filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("No such catalogue version.")
    if version.applications.exists():
        raise ConflictError(
            "A catalogue version used by an application cannot be changed.",
            code="version_in_use",
        )

    today = timezone.localdate()
    editable = version.status == "draft" or (
        version.status == "published"
        and version.effective_from is not None
        and version.effective_from > today
    )
    if not editable:
        raise ConflictError(
            "Only draft or unused future versions can be changed.",
            code="version_not_editable",
        )

    normalized = dict(changes)
    if "configuration" in normalized and not isinstance(normalized["configuration"], dict):
        raise BadRequestError("configuration must be a JSON object.", code="invalid_configuration")
    if "approval_reference" in normalized:
        value = normalized["approval_reference"]
        if not isinstance(value, str):
            raise BadRequestError(
                "approval_reference must be text.", code="invalid_approval_reference"
            )
        normalized["approval_reference"] = value.strip()

    proposed = {
        field: normalized.get(field, getattr(version, field))
        for field in (
            "effective_from",
            "effective_to",
            "application_opens_at",
            "application_closes_at",
            "renewal_opens_at",
            "renewal_closes_at",
        )
    }
    if not _date_values_are_ordered(proposed):
        raise BadRequestError("Catalogue date ranges must be ordered.", code="invalid_date_range")
    for field in ("effective_from", "effective_to"):
        value = normalized.get(field)
        if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
            raise BadRequestError(f"{field} has an invalid value.", code="invalid_date_range")
    for field in (
        "application_opens_at",
        "application_closes_at",
        "renewal_opens_at",
        "renewal_closes_at",
    ):
        value = normalized.get(field)
        if value is not None and not isinstance(value, datetime):
            raise BadRequestError(f"{field} has an invalid value.", code="invalid_date_range")

    before = {field: _audit_value(deepcopy(getattr(version, field))) for field in normalized}
    for field, value in normalized.items():
        setattr(version, field, value)
    version.save(update_fields=[*normalized, "updated_at"])
    after = _audit_values({field: getattr(version, field) for field in normalized})
    _audit(
        version=version,
        actor_user_id=actor_user_id,
        event_type="catalogue.version_updated",
        payload={"before": before, "after": after},
    )
    return version


@transaction.atomic
def publish_version(
    *,
    version_id: int,
    actor_user_id: int,
) -> CatalogueVersion:
    version = CatalogueVersion.objects.select_for_update().filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("No such catalogue version.")
    if version.status != "draft":
        raise ConflictError("Only a draft version can be published.", code="version_not_draft")
    if not version.approval_reference.strip():
        raise ConflictError(
            "An approval reference is required.", code="approval_reference_required"
        )
    if version.effective_from is None or version.effective_to is None:
        raise ConflictError("Effective dates are required.", code="effective_dates_required")
    if not _date_values_are_ordered(
        {
            "effective_from": version.effective_from,
            "effective_to": version.effective_to,
            "application_opens_at": version.application_opens_at,
            "application_closes_at": version.application_closes_at,
            "renewal_opens_at": version.renewal_opens_at,
            "renewal_closes_at": version.renewal_closes_at,
        }
    ):
        raise ConflictError("Catalogue date ranges must be ordered.", code="invalid_date_range")

    before = {"status": version.status}
    version.status = "published"
    version.published_at = timezone.now()
    version.published_by_user_id = actor_user_id
    version.save(
        update_fields=[
            "status",
            "published_at",
            "published_by_user_id",
            "updated_at",
        ]
    )
    _audit(
        version=version,
        actor_user_id=actor_user_id,
        event_type="catalogue.version_published",
        payload={
            "before": before,
            "after": {
                "status": version.status,
                "approval_reference": version.approval_reference,
                "effective_from": _audit_value(version.effective_from),
                "effective_to": _audit_value(version.effective_to),
            },
        },
    )
    return version


@transaction.atomic
def retire_version(
    *,
    version_id: int,
    actor_user_id: int,
) -> CatalogueVersion:
    version = CatalogueVersion.objects.select_for_update().filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("No such catalogue version.")
    if version.status != "published":
        raise ConflictError(
            "Only a published version can be retired.", code="version_not_published"
        )

    before = {"status": version.status}
    version.status = "retired"
    version.retired_at = timezone.now()
    version.retired_by_user_id = actor_user_id
    version.save(
        update_fields=[
            "status",
            "retired_at",
            "retired_by_user_id",
            "updated_at",
        ]
    )
    _audit(
        version=version,
        actor_user_id=actor_user_id,
        event_type="catalogue.version_retired",
        payload={"before": before, "after": {"status": version.status}},
    )
    return version


@transaction.atomic
def retire_entry(
    *,
    entry_id: int,
    actor_user_id: int,
) -> list[CatalogueVersion]:
    entry = CatalogueEntry.objects.select_for_update().filter(pk=entry_id).first()
    if entry is None:
        raise NotFoundError("No such catalogue entry.")

    today = timezone.localdate()
    versions = list(
        CatalogueVersion.objects.select_for_update()
        .filter(
            entry=entry,
            status="published",
            effective_to__gte=today,
        )
        .order_by("version_number")
    )
    if not versions:
        raise ConflictError(
            "The catalogue entry has no current or future published version.",
            code="no_published_version",
        )

    now = timezone.now()
    for version in versions:
        version.status = "retired"
        version.retired_at = now
        version.retired_by_user_id = actor_user_id
        version.save(
            update_fields=[
                "status",
                "retired_at",
                "retired_by_user_id",
                "updated_at",
            ]
        )
        _audit(
            version=version,
            actor_user_id=actor_user_id,
            event_type="catalogue.entry_retired",
            payload={
                "entry_id": entry.pk,
                "version_number": version.version_number,
                "before": {"status": "published"},
                "after": {"status": "retired"},
                "status": "retired",
            },
        )
    return versions


def published_catalogue(*, now: datetime | None = None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    return (
        CatalogueVersion.objects.filter(
            status="published",
            effective_from__lte=today,
            effective_to__gte=today,
        )
        .select_related("entry")
        .order_by("entry_id", "-version_number")
    )


def application_window_open(
    version: CatalogueVersion,
    *,
    now: datetime | None = None,
) -> bool:
    now = now or timezone.now()
    today = timezone.localdate(now)
    return bool(
        version.status == "published"
        and version.effective_from is not None
        and version.effective_to is not None
        and version.effective_from <= today <= version.effective_to
        and version.application_opens_at is not None
        and version.application_closes_at is not None
        and version.application_opens_at <= now <= version.application_closes_at
    )


def renewal_window_open(
    version: CatalogueVersion,
    *,
    now: datetime | None = None,
) -> bool:
    now = now or timezone.now()
    today = timezone.localdate(now)
    return bool(
        version.status == "published"
        and version.effective_from is not None
        and version.effective_to is not None
        and version.effective_from <= today <= version.effective_to
        and version.renewal_opens_at is not None
        and version.renewal_closes_at is not None
        and version.renewal_opens_at <= now <= version.renewal_closes_at
    )
