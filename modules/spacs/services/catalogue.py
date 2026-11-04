"""Catalogue and policy versioning services for SPACS.

Enforces:
- CFR-SPACS-002 (Catalogue Administration and Policy Versioning)
- BR-SPACS-014 (Published catalogue version is source of truth)
- BR-SPACS-015 (Catalogue must reflect approved policy)
- UC-SPACS-010, 011, 012, 023
"""
from __future__ import annotations

from datetime import date
from typing import Any
from django.db import transaction
from core.api.exceptions import ValidationError
from modules.spacs.models import CatalogueEntry, CataloguePolicyVersion
from modules.spacs.services.audit import record_audit_event


def create_catalogue_entry(
    code: str,
    title: str,
    kind: str,
    description: str,
    actor_user_id: int,
    actor_role: str = "spacs_convener",
) -> CatalogueEntry:
    """Creates a new draft catalogue entry (UC-SPACS-010)."""
    with transaction.atomic():
        entry = CatalogueEntry.objects.create(
            code=code,
            title=title,
            kind=kind,
            description=description,
            status="draft",
        )
        record_audit_event(
            action="catalogue.entry_created",
            entity_type="CatalogueEntry",
            entity_id=entry.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            details={"code": code, "kind": kind, "title": title},
        )
        return entry


def create_policy_version(
    catalogue_entry: CatalogueEntry,
    version_label: str,
    effective_from: date,
    effective_to: date | None = None,
    eligibility_schema: dict[str, Any] | None = None,
    required_evidence_schema: list[dict[str, Any]] | None = None,
    sla_config: dict[str, Any] | None = None,
    is_renewable: bool = False,
    renewal_window_start: Any = None,
    renewal_window_end: Any = None,
    max_renewal_cycles: int = 0,
    candidate_source_method: str = "application",
    eval_committee_role: str = "",
    approving_authority_title: str = "",
    actor_user_id: int | None = None,
    actor_role: str = "spacs_convener",
) -> CataloguePolicyVersion:
    """Creates a draft or future-effective policy version (UC-SPACS-011)."""
    with transaction.atomic():
        version = CataloguePolicyVersion.objects.create(
            catalogue_entry=catalogue_entry,
            version_label=version_label,
            effective_from=effective_from,
            effective_to=effective_to,
            eligibility_schema=eligibility_schema or {},
            required_evidence_schema=required_evidence_schema or [],
            sla_config=sla_config or {},
            is_renewable=is_renewable,
            renewal_window_start=renewal_window_start,
            renewal_window_end=renewal_window_end,
            max_renewal_cycles=max_renewal_cycles,
            candidate_source_method=candidate_source_method,
            eval_committee_role=eval_committee_role,
            approving_authority_title=approving_authority_title,
            is_published=False,
        )
        record_audit_event(
            action="catalogue.version_created",
            entity_type="CataloguePolicyVersion",
            entity_id=version.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            details={"entry_code": catalogue_entry.code, "version": version_label},
        )
        return version


def publish_policy_version(
    version: CataloguePolicyVersion,
    policy_approval_ref: str,
    policy_approval_date: date,
    actor_user_id: int,
    actor_role: str = "spacs_convener",
) -> CataloguePolicyVersion:
    """Publishes/activates a catalogue version (UC-SPACS-023).

    Guarded by BR-SPACS-015: requires formal approval reference and date.
    """
    if not policy_approval_ref or not policy_approval_ref.strip():
        raise ValidationError("Publication requires a formal policy approval reference (resolution or circular no).")

    if not policy_approval_date:
        raise ValidationError("Publication requires a recorded policy approval date.")

    with transaction.atomic():
        version.policy_approval_ref = policy_approval_ref.strip()
        version.policy_approval_date = policy_approval_date
        version.is_published = True
        version.save()

        # Update parent catalogue entry to active if not already
        entry = version.catalogue_entry
        if entry.status == "draft":
            entry.status = "active"
            entry.save()

        record_audit_event(
            action="catalogue.version_published",
            entity_type="CataloguePolicyVersion",
            entity_id=version.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            details={
                "version_label": version.version_label,
                "approval_ref": policy_approval_ref,
                "approval_date": str(policy_approval_date),
            },
        )
        return version


def retire_catalogue_entry(
    entry: CatalogueEntry,
    actor_user_id: int,
    actor_role: str = "spacs_convener",
) -> CatalogueEntry:
    """Retires a catalogue entry prospectively (UC-SPACS-012, AFR-SPACS-006)."""
    with transaction.atomic():
        entry.status = "retired"
        entry.save()

        record_audit_event(
            action="catalogue.entry_retired",
            entity_type="CatalogueEntry",
            entity_id=entry.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            details={"code": entry.code},
        )
        return entry
