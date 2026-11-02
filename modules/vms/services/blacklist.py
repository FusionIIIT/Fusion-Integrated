"""Blacklist check at the runtime checkpoints (VMS-BR-112, 116-120, decision D-2).

Reads the PUBLISHED version only. Writes belong to lane C
(`services/blacklist_admin.py`); `add_entry` is the port of the legacy POST.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from modules.vms.domain import blacklist_match
from modules.vms.models import (
    BlacklistEntry, BlacklistVersion, SafeListEntry,
)
from modules.vms.services.common import audit

CHECKPOINTS = ("pre_registration", "walk_in", "gate")


@dataclass(frozen=True)
class BlacklistHit:
    entry_id: int
    version: int
    severity: str
    reason: str
    matched_fields: tuple[str, ...]
    checkpoint: str


@dataclass(frozen=True)
class _Probe:
    id_doc_number: str = ""
    phone: str = ""
    email: str = ""


def published_version() -> BlacklistVersion | None:
    return (BlacklistVersion.objects.filter(status=BlacklistVersion.Status.PUBLISHED)
            .order_by("-version").first())


def _safe_listed(id_doc_number: str, at) -> bool:
    want = blacklist_match.norm_id(id_doc_number)
    if not want:
        return False
    rows = SafeListEntry.objects.filter(revoked_at__isnull=True, expires_at__gt=at)
    return any(blacklist_match.norm_id(v) == want
               for v in rows.values_list("visitor_id_doc_number", flat=True))


def check(*, checkpoint: str, name="", id_doc_number="", phone="", email="",
          at=None) -> BlacklistHit | None:
    """Return the worst matching hit, or None. `name` never matches (D-2)."""
    if checkpoint not in CHECKPOINTS:
        raise ValueError(f"unknown checkpoint {checkpoint!r}")
    at = at or timezone.now()
    version = published_version()
    if version is None:
        return None
    probe = _Probe(id_doc_number, phone, email)
    if not (blacklist_match.norm_id(id_doc_number) or blacklist_match.norm_phone(phone)
            or blacklist_match.norm_email(email)):
        return None
    hits = []
    entries = version.entries.filter(is_active=True).exclude(expiry_date__lt=at.date())
    for entry in entries:
        fields = blacklist_match.matched_fields(entry, probe)
        if fields:
            hits.append((entry, fields))
    if not hits:
        return None
    if _safe_listed(id_doc_number, at):      # BR-118/119
        return None
    entry, fields = max(hits, key=lambda h: blacklist_match.severity_rank(h[0].severity))
    return BlacklistHit(entry_id=entry.pk, version=version.version,
                        severity=entry.severity, reason=entry.reason,
                        matched_fields=tuple(fields), checkpoint=checkpoint)


def add_entry(*, actor, **fields) -> BlacklistEntry:
    """Legacy POST (TODO lane C: replace with blacklist_admin). Adds to the
    published version, creating published v1 if none exists, so an added entry
    takes effect as it did before versioning."""
    version = published_version()
    if version is None:
        version = BlacklistVersion.objects.create(
            version=1, status=BlacklistVersion.Status.PUBLISHED,
            published_at=timezone.now(), published_by_user_id=getattr(actor, "user_id", None))
    entry = BlacklistEntry.objects.create(version=version, **fields)
    audit.record(actor=actor, action="vms.blacklist.entry_added", entity=entry,
                 detail={"version": version.version})
    return entry
