"""Catalogue and versioned policy models for SPACS.

Enforces:
- CFR-SPACS-001 (Published Catalogue Access)
- CFR-SPACS-002 (Catalogue Administration & Policy Versioning)
- BR-SPACS-014 (Published catalogue version is source of truth)
- BR-SPACS-015 (Catalogue must reflect approved policy)
- BR-SPACS-020 (Award criteria versioning)
"""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class CatalogueEntry(TimeStampedModel):
    """An opportunity entry in the SPACS catalogue."""

    KINDS = [
        ("scholarship", "Scholarship Scheme"),
        ("award", "Convocation Award / Prize"),
    ]
    STATUSES = [
        ("draft", "Draft"),
        ("active", "Active / Published"),
        ("retired", "Retired"),
    ]

    code = models.SlugField(max_length=60, unique=True, db_index=True)
    title = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=KINDS)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="draft")

    class Meta:
        db_table = "spacs_catalogue_entry"
        ordering = ["title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.code})"


class CataloguePolicyVersion(TimeStampedModel):
    """An effective-dated, versioned policy governing an entry.

    Historical applications retain the exact version in effect at their submission.
    """

    catalogue_entry = models.ForeignKey(
        CatalogueEntry, on_delete=models.CASCADE, related_name="versions"
    )
    version_label = models.CharField(max_length=32)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    # Approved policy provenance (Mandatory for publication - BR-SPACS-015)
    policy_approval_ref = models.CharField(max_length=150, blank=True)
    policy_approval_date = models.DateField(null=True, blank=True)

    # Application & Renewal Windows
    application_window_start = models.DateTimeField(null=True, blank=True)
    application_window_end = models.DateTimeField(null=True, blank=True)
    is_renewable = models.BooleanField(default=False)
    renewal_window_start = models.DateTimeField(null=True, blank=True)
    renewal_window_end = models.DateTimeField(null=True, blank=True)
    max_renewal_cycles = models.PositiveSmallIntegerField(default=0)

    # Convocation Award Configuration (BR-SPACS-019, BR-SPACS-023)
    candidate_source_method = models.CharField(
        max_length=30,
        choices=[
            ("application", "Student Application"),
            ("system_pool", "System Record Pool"),
            ("nomination", "Faculty Nomination"),
        ],
        default="application",
    )
    eval_committee_role = models.CharField(
        max_length=80, blank=True,
        help_text="Role or committee designation authorized to evaluate candidates"
    )
    approving_authority_title = models.CharField(
        max_length=120, blank=True,
        help_text="Name of the final sanctioning body (e.g. Senate, Board of Governors, Director)"
    )

    # Configurable Policy Schemas (No hardcoded criteria - BR-SPACS-001, BR-SPACS-004)
    eligibility_schema = models.JSONField(
        default=dict, blank=True,
        help_text="Machine-checkable criteria: min_cpi, max_annual_income, allowed_programmes, etc."
    )
    required_evidence_schema = models.JSONField(
        default=list, blank=True,
        help_text="List of required evidence configs: doc_type, description, mandatory, max_age_days"
    )
    sla_config = models.JSONField(
        default=dict, blank=True,
        help_text="Configured SLA reminder & escalation stages for this scheme"
    )

    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "spacs_policy_version"
        ordering = ["-effective_from", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["catalogue_entry", "version_label"],
                name="spacs_policy_version_unique_label",
            )
        ]

    def __str__(self) -> str:
        return f"{self.catalogue_entry.code} - {self.version_label}"
