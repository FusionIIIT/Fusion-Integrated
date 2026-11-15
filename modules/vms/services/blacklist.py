"""The blacklist/watchlist and safe-list runtime checks.

VMS-BR-001: matching uses exact quorum/ID/other-match — NO partial match.
Both sides of the comparison are normalised (case, separators) so that
'ab-1234' and 'AB 1234' collide, but a substring of either never does.
"""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from modules.vms.models import (
    BlacklistRecord,
    SafeListRecord,
    Visitor,
    normalize_id,
)
from modules.vms.services.alerts import open_alert
from modules.vms.services.errors import BlacklistBlockedError


def _exact_q(*, full_name: str = "", phone: str = "",
             email: str = "", id_doc_number: str = "") -> Q:
    """Only equality clauses. Never icontains — that is VMS-BR-001."""
    q = Q()
    if id_doc_number:
        q |= Q(id_doc_normalized=normalize_id(id_doc_number))
    if phone:
        q |= Q(phone=phone.strip())
    if email:
        q |= Q(email__iexact=email.strip())
    if full_name:
        # Full name matches case-insensitively but WHOLE, not by substring.
        q |= Q(full_name__iexact=full_name.strip())
    return q


def find_matches(*, full_name: str = "", phone: str = "",
                 email: str = "", id_doc_number: str = "",
                 active_only: bool = True) -> list[BlacklistRecord]:
    """Active registry rows that EXACTLY match any supplied identifier."""
    q = _exact_q(full_name=full_name, phone=phone, email=email,
                 id_doc_number=id_doc_number)
    if not q:
        return []
    rows = BlacklistRecord.objects.filter(q)
    if active_only:
        today = timezone.localdate()
        rows = rows.filter(is_active=True).filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
    return list(rows)


def is_blocked(**identifiers) -> bool:
    return bool(find_matches(**identifiers))


def assert_registration_allowed(visitor: Visitor, *, context: str = "registration") -> None:
    """VMS-BR-004 (registration) and VMS-BR-024 (registration request):
    an active match blocks the request AND raises a gate alert.

    VMS-BR-011: this must be called from BOTH the visit-request path and
    the walk-in registration path.
    """
    hits = find_matches(
        full_name=visitor.full_name, phone=visitor.phone,
        email=visitor.email, id_doc_number=visitor.id_doc_number)
    if not hits:
        return
    top = max(hits, key=lambda r: (r.severity == "HIGH", r.date_added))
    open_alert(
        alert_type="BLACKLIST_HIT",
        severity=top.severity,
        message=(f"Blacklist match for {visitor.full_name} at {context}: "
                 f"{top.reason}"),
        visitor_id=visitor.id,
        dedupe=True,
    )
    raise BlacklistBlockedError(
        f"Visitor matches {top.kind} entry: {top.reason}",
        details=[{"rule": top.kind, "severity": top.severity,
                  "reason": top.reason}])


def find_safe_list(*, full_name: str = "", phone: str = "",
                   email: str = "", id_doc_number: str = "") -> SafeListRecord | None:
    """An unexpired, active safe-list row matching exactly (VMS-BR-015)."""
    q = _exact_q(full_name=full_name, phone=phone, email=email,
                 id_doc_number=id_doc_number)
    if not q:
        return None
    today = timezone.localdate()
    return (SafeListRecord.objects
            .filter(q, is_active=True)
            .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
            .first())


def is_safe_listed(visitor: Visitor) -> bool:
    return find_safe_list(full_name=visitor.full_name, phone=visitor.phone,
                          email=visitor.email,
                          id_doc_number=visitor.id_doc_number) is not None


def add_record(*, kind: str = "BLACKLIST", full_name: str = "",
               phone: str = "", email: str = "",
               id_doc_type: str = "OTHER", id_doc_number: str = "",
               reason: str, severity: str = "MEDIUM",
               expiry_date=None, added_by_user_id: int | None = None,
               ) -> BlacklistRecord:
    return BlacklistRecord.objects.create(
        kind=kind, full_name=full_name, phone=phone, email=email,
        id_doc_type=id_doc_type, id_doc_number=id_doc_number,
        id_doc_normalized=normalize_id(id_doc_number), reason=reason,
        severity=severity, expiry_date=expiry_date,
        added_by_user_id=added_by_user_id)


def deactivate_record(record: BlacklistRecord) -> BlacklistRecord:
    record.is_active = False
    record.save(update_fields=["is_active", "updated_at"])
    return record
