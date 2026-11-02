"""Visitor identity and the registries that gate entry.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. A visitor is a VMS-local row:
guests are not institute accounts.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


def normalize_id(value: str) -> str:
    """Uppercase, strip separators. Used by BOTH sides of a blacklist
    comparison so 'ab-1234' and 'AB 1234' collide — while the comparison
    itself stays exact (VMS-BR-001: no partial matching)."""
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


class Visitor(TimeStampedModel):
    ID_DOC_TYPES = [
        ("AADHAAR", "Aadhaar"), ("PAN", "PAN"), ("PASSPORT", "Passport"),
        ("DRIVING_LICENSE", "Driving Licence"), ("COLLEGE_ID", "College ID"),
        ("OTHER", "Other"),
    ]

    full_name = models.CharField(max_length=160, db_index=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    id_doc_type = models.CharField(max_length=24, choices=ID_DOC_TYPES,
                                   default="OTHER")
    id_doc_number = models.CharField(max_length=64, blank=True)
    #: Normalised form the registries compare against (VMS-BR-001).
    id_doc_normalized = models.CharField(max_length=64, blank=True,
                                         db_index=True)
    photo_url = models.URLField(blank=True)
    #: VMS-BR-013 — an anonymous visitor has no QR identity.
    is_anonymous = models.BooleanField(default=False)
    #: VMS-BR-027 — denied visit disables the visitor.
    is_disabled = models.BooleanField(default=False)
    disabled_reason = models.CharField(max_length=255, blank=True)
    #: Campus account if the guest also has one; null for pure visitors.
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_visitor"
        indexes = [
            models.Index(fields=["phone", "email"],
                         name="vms_visitor_contact_idx"),
            models.Index(fields=["full_name", "id_doc_normalized"],
                         name="vms_visitor_match_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.id or '?'}>"

    @property
    def is_active(self) -> bool:
        return not self.is_disabled

    @property
    def identity_type(self) -> str:
        return self.id_doc_type

    @property
    def id_number(self) -> str:
        return self.id_doc_number

    @property
    def organization(self) -> str:
        return ""



class BlacklistRecord(TimeStampedModel):
    """A prohibited (or watched) person. Only PUBLISHED/active rows are
    consumed at runtime; matching is exact on the normalised fields."""

    KINDS = [("BLACKLIST", "Blacklist"), ("WATCHLIST", "Watchlist")]
    SEVERITIES = [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")]

    kind = models.CharField(max_length=16, choices=KINDS, default="BLACKLIST")
    full_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    id_doc_type = models.CharField(max_length=24, choices=Visitor.ID_DOC_TYPES,
                                   default="OTHER")
    id_doc_number = models.CharField(max_length=64, blank=True)
    id_doc_normalized = models.CharField(max_length=64, blank=True,
                                         db_index=True)
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=8, choices=SEVERITIES,
                                default="MEDIUM")
    date_added = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    added_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_blacklist_record"
        indexes = [
            models.Index(fields=["kind", "is_active"],
                         name="vms_blacklist_kind_idx"),
            models.Index(fields=["phone", "email"],
                         name="vms_blacklist_contact_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.full_name or self.id_doc_normalized}"


class SafeListRecord(TimeStampedModel):
    """Temporary safe-list for vetted VIPs/vendors (VMS-BR-015). Being on it
    grants NO implicit zone access — only expedited review."""

    full_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    id_doc_type = models.CharField(max_length=24, choices=Visitor.ID_DOC_TYPES,
                                   default="OTHER")
    id_doc_number = models.CharField(max_length=64, blank=True)
    id_doc_normalized = models.CharField(max_length=64, blank=True,
                                         db_index=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.CharField(max_length=255, blank=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_safe_list_record"
        indexes = [
            models.Index(fields=["is_active", "expiry_date"],
                         name="vms_safelist_active_idx"),
        ]


class Alert(TimeStampedModel):
    TYPES = [
        ("BLACKLIST_HIT", "Blacklist hit"),
        ("ZONE_VIOLATION", "Zone violation"),
        ("GATE_VALIDATION_FAILURE", "Gate validation failure"),
        ("SUSPICIOUS_GATE_CASE", "Suspicious gate case"),
        ("EMERGENCY_MUSTER", "Emergency muster"),
    ]
    STATUS = [("OPEN", "Open"), ("CLOSED", "Closed")]

    alert_type = models.CharField(max_length=32, choices=TYPES)
    severity = models.CharField(max_length=8, choices=BlacklistRecord.SEVERITIES,
                                default="MEDIUM")
    message = models.CharField(max_length=255)
    visitor_id = models.IntegerField(null=True, blank=True, db_index=True)
    visit_id = models.IntegerField(null=True, blank=True, db_index=True)
    pass_id = models.IntegerField(null=True, blank=True)
    zone_code = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default="OPEN",
                              db_index=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by_user_id = models.IntegerField(null=True, blank=True)
    #: VMS-BR-002/028 — closed by the system, not by a person.
    auto_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "vms_alert"
        indexes = [
            models.Index(fields=["status", "alert_type"],
                         name="vms_alert_status_idx"),
            models.Index(fields=["visitor_id", "status"],
                         name="vms_alert_visitor_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.alert_type}:{self.status}:{self.id}"
