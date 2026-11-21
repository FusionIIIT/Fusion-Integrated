"""SPACS Catalogue Administration Service (CFR-SPACS-001, CFR-SPACS-002)."""

from datetime import date
from django.utils import timezone

from ..domain.rules import (
    validate_catalogue_publication_prerequisites,
)
from ..domain.errors import SpacsDomainError
from ..models import SpacsCatalogueEntry, SpacsCatalogueVersion
from .audit import log_action


def create_catalogue_entry(
    scheme_code: str,
    name: str,
    scheme_type: str,
    created_by_user_id: int,
    description: str = "",
    min_cpi: float = 0.0,
    max_family_income: float | None = None,
    required_documents: list[str] | None = None,
    application_window_start=None,
    application_window_end=None,
    renewal_allowed: bool = False,
    renewal_window_start=None,
    renewal_window_end=None,
    candidate_source_method: str = "application",
    academic_cycle: str = "2026-27",
) -> SpacsCatalogueEntry:
    """Create a draft catalogue entry (AFR-SPACS-003)."""
    entry = SpacsCatalogueEntry.objects.create(
        scheme_code=scheme_code,
        name=name,
        scheme_type=scheme_type,
        description=description,
        status="draft",
        min_cpi=min_cpi,
        max_family_income=max_family_income,
        required_documents=required_documents or [],
        application_window_start=application_window_start,
        application_window_end=application_window_end,
        renewal_allowed=renewal_allowed,
        renewal_window_start=renewal_window_start,
        renewal_window_end=renewal_window_end,
        candidate_source_method=candidate_source_method,
        academic_cycle=academic_cycle,
        created_by_user_id=created_by_user_id,
        version=1,
    )
    log_action(
        event_type="catalogue_entry_created",
        entity_type="catalogue_entry",
        entity_id=entry.scheme_code,
        actor_user_id=created_by_user_id,
        details={"name": name, "status": "draft", "version": 1},
    )
    return entry


def update_draft_catalogue_entry(
    scheme_code: str,
    actor_user_id: int,
    **updates,
) -> SpacsCatalogueEntry:
    """Update a draft catalogue entry without altering published/historical records (AFR-SPACS-004)."""
    entry = SpacsCatalogueEntry.objects.get(scheme_code=scheme_code)
    if entry.status == "retired":
        raise SpacsDomainError(f"Cannot update retired catalogue entry '{scheme_code}'.")

    # If it is published, modifying criteria increments the version (AFR-SPACS-004, AFR-SPACS-007)
    if entry.status == "published":
        entry.version += 1
        entry.status = "draft"

    for field, val in updates.items():
        if hasattr(entry, field):
            setattr(entry, field, val)

    entry.save()
    log_action(
        event_type="catalogue_entry_updated",
        entity_type="catalogue_entry",
        entity_id=entry.scheme_code,
        actor_user_id=actor_user_id,
        details={"updates": updates, "version": entry.version},
    )
    return entry


def publish_catalogue_version(
    scheme_code: str,
    policy_approval_ref: str,
    effective_from: date,
    actor_user_id: int,
    effective_to: date | None = None,
) -> SpacsCatalogueEntry:
    """Publish/activate a catalogue version with approved-policy provenance (AFR-SPACS-005, BR-SPACS-015)."""
    validate_catalogue_publication_prerequisites(policy_approval_ref, effective_from, effective_to)

    entry = SpacsCatalogueEntry.objects.get(scheme_code=scheme_code)
    entry.policy_approval_ref = policy_approval_ref
    entry.effective_from = effective_from
    entry.effective_to = effective_to
    entry.status = "published"
    entry.save()

    # Create immutable version record for auditability (AFR-SPACS-007, BR-SPACS-014)
    SpacsCatalogueVersion.objects.create(
        catalogue_entry=entry,
        version=entry.version,
        policy_approval_ref=policy_approval_ref,
        effective_from=effective_from,
        effective_to=effective_to,
        criteria_snapshot={
            "name": entry.name,
            "min_cpi": float(entry.min_cpi),
            "max_family_income": float(entry.max_family_income) if entry.max_family_income else None,
            "required_documents": entry.required_documents,
            "renewal_allowed": entry.renewal_allowed,
            "candidate_source_method": entry.candidate_source_method,
        },
    )

    log_action(
        event_type="catalogue_version_published",
        entity_type="catalogue_entry",
        entity_id=entry.scheme_code,
        actor_user_id=actor_user_id,
        details={
            "version": entry.version,
            "policy_approval_ref": policy_approval_ref,
            "effective_from": str(effective_from),
        },
    )
    return entry


def retire_catalogue_entry(scheme_code: str, actor_user_id: int) -> SpacsCatalogueEntry:
    """Retire/deactivate a catalogue entry prospectively (AFR-SPACS-006)."""
    entry = SpacsCatalogueEntry.objects.get(scheme_code=scheme_code)
    entry.status = "retired"
    entry.save()

    log_action(
        event_type="catalogue_entry_retired",
        entity_type="catalogue_entry",
        entity_id=entry.scheme_code,
        actor_user_id=actor_user_id,
        details={"scheme_code": scheme_code},
    )
    return entry


def get_published_catalogue_entries():
    """Retrieve all currently published catalogue entries (AFR-SPACS-001)."""
    return SpacsCatalogueEntry.objects.filter(status="published")
