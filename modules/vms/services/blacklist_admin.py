"""Versioned blacklist and safe-list administration (VMS-UC-005, CFR-007, BR-116..120).

Entries are edited only inside a draft version; ``blacklist.check`` reads only
the published one (BR-120). Entries are never hard-deleted: they are
deactivated. A new draft starts as a copy of the published version, because
publishing replaces the runtime list as a whole.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.domain import blacklist_match
from modules.vms.models import BlacklistEntry, BlacklistVersion, SafeListEntry
from modules.vms.services import blacklist as blacklist_read
from modules.vms.services.common import audit, authz

MANAGE = "vms.blacklist.manage"
PUBLISH = "vms.blacklist.publish"
SAFELIST = "vms.safelist.manage"
SAFELIST_MAX_DAYS = 90      # D-7
EDITABLE = ("name", "id_doc_number", "phone", "email", "reason", "severity",
            "expiry_date", "is_active")
_COPY = EDITABLE

Status = BlacklistVersion.Status


def _clean(fields: dict, *, partial: bool) -> dict:
    unknown = sorted(set(fields) - set(EDITABLE))
    if unknown:
        raise BadRequestError(f"Unknown field(s): {', '.join(unknown)}.",
                              code="validation_error")
    if not partial and (not fields.get("name") or not fields.get("reason")):
        raise BadRequestError("name and reason are required.", code="validation_error")
    if "severity" in fields and fields["severity"] not in blacklist_match.SEVERITIES:
        raise BadRequestError("severity must be low, medium, high or critical.",
                              code="validation_error")
    expiry = fields.get("expiry_date")
    if expiry is not None and expiry < timezone.localdate():
        raise BadRequestError("expiry_date is already in the past.", code="validation_error")
    return fields


def _has_identifier(fields: dict) -> bool:
    return any(fields.get(k) for k in ("id_doc_number", "phone", "email"))


def _draft_for_update(version_id: int) -> BlacklistVersion:
    version = BlacklistVersion.objects.select_for_update().filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("Blacklist version not found.")
    if version.status != Status.DRAFT:
        raise ConflictError("Only a draft version can be edited.", code="not_a_draft")
    return version


def get_version(version_id: int) -> BlacklistVersion:
    v = BlacklistVersion.objects.filter(pk=version_id).first()
    if v is None:
        raise NotFoundError("Blacklist version not found.")
    return v


def _new_draft(actor) -> BlacklistVersion:
    latest = BlacklistVersion.objects.select_for_update().order_by("-version").first()
    base = blacklist_read.published_version()
    draft = BlacklistVersion.objects.create(
        version=(latest.version if latest else 0) + 1, status=Status.DRAFT)
    copied = 0
    if base is not None:
        for e in base.entries.all():
            BlacklistEntry.objects.create(
                version=draft, **{f: getattr(e, f) for f in _COPY})
            copied += 1
    audit.record(actor=actor, action="vms.blacklist.draft_created", entity=draft,
                 detail={"version": draft.version, "copied_entries": copied,
                         "base_version": base.version if base else None})
    return draft


def create_version(*, actor) -> BlacklistVersion:
    authz.require(actor, MANAGE)
    with transaction.atomic():
        if BlacklistVersion.objects.filter(status=Status.DRAFT).exists():
            raise ConflictError("A draft blacklist version already exists.",
                                code="draft_exists")
        return _new_draft(actor)


def open_draft(*, actor) -> BlacklistVersion:
    """The current draft, created if none exists (used by the flat legacy endpoint)."""
    authz.require(actor, MANAGE)
    with transaction.atomic():
        draft = BlacklistVersion.objects.filter(status=Status.DRAFT).order_by("-version").first()
        return draft or _new_draft(actor)


def add_entry(*, actor, version_id: int, **fields) -> BlacklistEntry:
    authz.require(actor, MANAGE)
    fields = _clean(fields, partial=False)
    if not _has_identifier(fields):
        raise BadRequestError("Give at least one of id_doc_number, phone or email "
                              "(a name alone never matches).", code="validation_error")
    with transaction.atomic():
        version = _draft_for_update(version_id)
        entry = BlacklistEntry.objects.create(version=version, **fields)
        audit.record(actor=actor, action="vms.blacklist.entry_added", entity=entry,
                     detail={"version": version.version, "severity": entry.severity})
    return entry


def _entry_in_draft(entry_id: int, version_id: int) -> BlacklistEntry:
    entry = (BlacklistEntry.objects.select_for_update()
             .filter(pk=entry_id, version_id=version_id).first())
    if entry is None:
        raise NotFoundError("Entry not found.")
    return entry


def update_entry(*, actor, version_id: int, entry_id: int, **fields) -> BlacklistEntry:
    authz.require(actor, MANAGE)
    fields = _clean(fields, partial=True)
    with transaction.atomic():
        version = _draft_for_update(version_id)
        entry = _entry_in_draft(entry_id, version_id)
        for k, v in fields.items():
            setattr(entry, k, v)
        if entry.is_active and not _has_identifier(
                {k: getattr(entry, k) for k in ("id_doc_number", "phone", "email")}):
            raise BadRequestError("An active entry needs an id document, phone or email.",
                                  code="validation_error")
        entry.save()
        audit.record(actor=actor, action="vms.blacklist.entry_updated", entity=entry,
                     detail={"version": version.version, "fields": sorted(fields)})
    return entry


def deactivate_entry(*, actor, version_id: int, entry_id: int) -> BlacklistEntry:
    """Entries are never deleted; deactivation is the removal."""
    authz.require(actor, MANAGE)
    with transaction.atomic():
        version = _draft_for_update(version_id)
        entry = _entry_in_draft(entry_id, version_id)
        entry.is_active = False
        entry.save(update_fields=["is_active"])
        audit.record(actor=actor, action="vms.blacklist.entry_deactivated", entity=entry,
                     detail={"version": version.version})
    return entry


def _key(e: BlacklistEntry) -> tuple:
    return (blacklist_match.norm_id(e.id_doc_number), blacklist_match.norm_phone(e.phone),
            blacklist_match.norm_email(e.email))


def changelog(old: BlacklistVersion | None, new: BlacklistVersion) -> dict:
    """Active entries added / removed / changed between two versions (matched by
    normalised identifiers). Ids only: no personal data in the audit detail."""
    old_rows = {_key(e): e for e in old.entries.filter(is_active=True)} if old else {}
    new_rows = {_key(e): e for e in new.entries.filter(is_active=True)}
    added = [e.pk for k, e in new_rows.items() if k not in old_rows]
    removed = [e.pk for k, e in old_rows.items() if k not in new_rows]
    changed = [e.pk for k, e in new_rows.items() if k in old_rows and any(
        getattr(e, f) != getattr(old_rows[k], f)
        for f in ("severity", "reason", "expiry_date", "name"))]
    return {"added": added, "removed": removed, "changed": changed}


def publish(*, actor, version_id: int) -> BlacklistVersion:
    """BR-120: the published version becomes the only one `check` reads."""
    authz.require(actor, PUBLISH)
    with transaction.atomic():
        version = _draft_for_update(version_id)
        previous = blacklist_read.published_version()
        if previous is not None and not any(changelog(previous, version).values()):
            raise BadRequestError("The draft has no changes from the live version.",
                                  code="no_changes")
        newest = BlacklistVersion.objects.filter(status=Status.PUBLISHED).aggregate(
            m=Max("version"))["m"] or 0
        if version.version < newest:
            raise ConflictError("A newer version is already published.", code="stale_draft")
        version.status = Status.PUBLISHED
        version.published_at = timezone.now()
        version.published_by_user_id = actor.user_id
        version.save(update_fields=["status", "published_at", "published_by_user_id"])
        audit.record(actor=actor, action="vms.blacklist.published", entity=version,
                     detail={"version": version.version,
                             "previous_version": previous.version if previous else None,
                             "changelog": changelog(previous, version)})
    return version


# --- safe list (BR-118/119, D-7) -------------------------------------------------------

def add_safelist(*, actor, id_doc_number: str, reason: str, expires_at) -> SafeListEntry:
    authz.require(actor, SAFELIST)
    now = timezone.now()
    if not blacklist_match.norm_id(id_doc_number) or not reason:
        raise BadRequestError("id_doc_number and reason are required.",
                              code="validation_error")
    if expires_at is None or expires_at <= now:
        raise BadRequestError("A safe-list entry needs a future expiry (BR-119).",
                              code="validation_error")
    if expires_at > now + timedelta(days=SAFELIST_MAX_DAYS):
        raise BadRequestError(f"A safe-list entry may last at most {SAFELIST_MAX_DAYS} days.",
                              code="validation_error")
    with transaction.atomic():
        entry = SafeListEntry.objects.create(
            visitor_id_doc_number=id_doc_number, reason=reason, expires_at=expires_at,
            created_by_user_id=actor.user_id)
        audit.record(actor=actor, action="vms.safelist.added", entity=entry,
                     detail={"expires_at": expires_at.isoformat()})
    return entry


def revoke_safelist(*, actor, entry_id: int) -> SafeListEntry:
    authz.require(actor, SAFELIST)
    with transaction.atomic():
        entry = SafeListEntry.objects.select_for_update().filter(pk=entry_id).first()
        if entry is None:
            raise NotFoundError("Safe-list entry not found.")
        if entry.revoked_at is not None:
            raise ConflictError("Already revoked.", code="already_revoked")
        entry.revoked_at = timezone.now()
        entry.save(update_fields=["revoked_at"])
        audit.record(actor=actor, action="vms.safelist.revoked", entity=entry)
    return entry
